import os
import pickle
import time
from typing import Any

import numpy as np

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
EMBEDDING_DIM = 8  # Example dimension, should match generate_embedding_tool


def batch_generate_embeddings(
    index_name: str, overwrite: bool = False
) -> dict[str, Any]:
    """
    Generates mock embeddings for all nodes in the index that don't already have one,
    or overwrites existing embeddings if specified.

    Args:
        index_name: The name of the FAISS index whose metadata to update.
        overwrite: If True, generate and overwrite embeddings even if they already exist.

    Returns:
        A dictionary with status, count of nodes processed, and count of embeddings generated/updated.

    Raises:
        IOError: If loading or saving the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    index_path = os.path.join(FAISS_DIR, f"{index_name}.faiss")

    if not os.path.exists(meta_path) or not os.path.exists(index_path):
        return {
            "status": "failed",
            "error": f"FAISS index or metadata file not found for '{index_name}'.",
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
                "error": f"Metadata file disappeared for index '{index_name}' during batch embedding.",
            }
        except Exception as e:
            print(
                f"Attempt {attempt + 1} failed to load metadata for FAISS index '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise OSError(
                    f"Failed to load metadata for FAISS index '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    if (
        loaded_data is None
        or "metadata" not in loaded_data
        or "id_to_key" not in loaded_data
        or "key_to_id" not in loaded_data
    ):
        raise ValueError(f"Invalid metadata file format for '{index_name}'.")

    metadata_dict = loaded_data["metadata"]
    generated_count = 0
    processed_count = 0
    needs_saving = False

    # --- Generate Embeddings ---
    for key, item_metadata in metadata_dict.items():
        processed_count += 1
        if not isinstance(item_metadata, dict):
            print(f"Warning: Skipping key '{key}' as its value is not a dictionary.")
            continue

        if overwrite or "embedding" not in item_metadata:
            mock_embedding = np.random.rand(EMBEDDING_DIM).tolist()
            item_metadata["embedding"] = mock_embedding
            metadata_dict[key] = item_metadata  # Ensure update is reflected
            generated_count += 1
            needs_saving = True

    if not needs_saving:
        print(
            f"No embeddings needed generation (or overwrite=False) for index '{index_name}'. Processed {processed_count} nodes."
        )
        return {
            "status": "success",
            "processed_nodes": processed_count,
            "embeddings_generated": 0,
        }

    loaded_data["metadata"] = metadata_dict

    # --- Save with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)

            print(
                f"Successfully batch generated/updated {generated_count} embeddings for index '{index_name}'. Processed {processed_count} nodes."
            )
            return {
                "status": "success",
                "processed_nodes": processed_count,
                "embeddings_generated": generated_count,
            }

        except Exception as e:
            print(
                f"Attempt {attempt + 1} failed to save metadata after batch generating embeddings for '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise OSError(
                    f"Failed to save metadata after batch generating embeddings for '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    return {
        "status": "failed",
        "error": "Unknown error after batch generating embeddings and save attempts.",
    }


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_semantic_test exists
    print("Batch generating embeddings for index_semantic_test (overwrite=False):")
    try:
        # doc_sem1 already has embedding, doc_sem2 might from similarity test setup
        print(batch_generate_embeddings("index_semantic_test", overwrite=False))
    except Exception as e:
        print(f"Error: {e}")

    print("\nBatch generating embeddings for index_semantic_test (overwrite=True):")
    try:
        print(batch_generate_embeddings("index_semantic_test", overwrite=True))
    except Exception as e:
        print(f"Error: {e}")

    # Verify change
    print("\nVerifying embeddings using load tool:")
    from load_metadata_from_faiss_tool import load_metadata_from_faiss

    try:
        updated_data = load_metadata_from_faiss("index_semantic_test")
        print(updated_data)
    except Exception as e:
        print(f"Error verifying: {e}")
