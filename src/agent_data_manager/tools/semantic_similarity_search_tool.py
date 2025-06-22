import pickle
import os
import time
from typing import Dict, Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
SIMILARITY_THRESHOLD = 0.2  # Arbitrary threshold for mock similarity (on first element)
TOP_N = 5  # Max number of similar items to return


def semantic_similarity_search(index_name: str, target_key: str, top_n: int = TOP_N) -> Dict[str, Any]:
    """
    Simulates semantic similarity search based on mock embeddings.
    Finds items whose first embedding element is close to the target key's first element.

    Args:
        index_name: The name of the FAISS index to search within.
        target_key: The key of the item to find similar items for.
        top_n: The maximum number of similar items to return.

    Returns:
        A dictionary with status: success and a list of similar items (key and mock score),
        or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for index '{index_name}'. Cannot perform similarity search.",
        }

    loaded_data = None
    # --- Load with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break
        except FileNotFoundError:
            return {
                "status": "failed",
                "error": f"Metadata file disappeared for index '{index_name}' during similarity search.",
            }
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to load metadata for FAISS index '{index_name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise IOError(
                    f"Failed to load metadata for FAISS index '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    if loaded_data is None or "metadata" not in loaded_data:
        raise ValueError(f"Invalid metadata file format for '{index_name}'.")

    metadata_dict = loaded_data["metadata"]

    if target_key not in metadata_dict:
        return {"status": "failed", "error": f"Target key '{target_key}' not found in index '{index_name}'."}

    target_metadata = metadata_dict[target_key]
    if (
        not isinstance(target_metadata, dict)
        or "embedding" not in target_metadata
        or not isinstance(target_metadata["embedding"], list)
        or not target_metadata["embedding"]
    ):
        return {"status": "failed", "error": f"Target key '{target_key}' does not have a valid embedding."}

    target_emb_val = target_metadata["embedding"][0]  # Use first element for mock similarity
    similar_items = []

    for key, item_metadata in metadata_dict.items():
        if key == target_key:
            continue  # Don't compare item to itself

        if (
            isinstance(item_metadata, dict)
            and "embedding" in item_metadata
            and isinstance(item_metadata["embedding"], list)
            and item_metadata["embedding"]
        ):
            try:
                compare_emb_val = item_metadata["embedding"][0]
                # Mock similarity: absolute difference of the first element
                diff = abs(target_emb_val - compare_emb_val)
                if diff <= SIMILARITY_THRESHOLD:
                    # Score inversely proportional to difference (closer is better)
                    mock_score = 1.0 - (diff / SIMILARITY_THRESHOLD)
                    similar_items.append({"key": key, "mock_similarity_score": round(mock_score, 4)})
            except (IndexError, TypeError) as e:
                print(f"Warning: Error processing embedding for key '{key}': {e}. Skipping.")

    # Sort by score descending and take top N
    sorted_similar = sorted(similar_items, key=lambda x: x["mock_similarity_score"], reverse=True)
    top_similar = sorted_similar[:top_n]

    print(f"Found {len(top_similar)} similar items (mock) for key '{target_key}' in index '{index_name}'.")
    return {"status": "success", "target_key": target_key, "similar_items": top_similar}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_semantic_test exists and generate_embedding was run
    # We need to ensure multiple items have embeddings for a meaningful test
    from generate_embedding_tool import generate_embedding

    try:
        print(generate_embedding("index_semantic_test", "doc_sem2"))  # Ensure doc_sem2 also has an embedding
    except Exception as e:
        print(f"Error generating embedding for doc_sem2: {e}")

    print("\nSearching for items similar to doc_sem1:")
    try:
        print(semantic_similarity_search("index_semantic_test", "doc_sem1"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nSearching for items similar to doc_sem2:")
    try:
        print(semantic_similarity_search("index_semantic_test", "doc_sem2"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nSearching for non-existent key:")
    try:
        print(semantic_similarity_search("index_semantic_test", "doc_sem_nonexistent"))
    except Exception as e:
        print(f"Error: {e}")
