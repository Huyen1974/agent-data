import os
import pickle
import time
from typing import Any

import numpy as np

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
EMBEDDING_DIM = 8  # Example dimension for mock embeddings


def generate_embedding(index_name: str, key: str) -> dict[str, Any]:
    """
    Generates a mock embedding for a specific metadata node and updates the metadata file.

    Args:
        index_name: The name of the FAISS index whose metadata to update.
        key: The key of the metadata node to generate embedding for.

    Returns:
        A dictionary with status: success and the generated embedding (as a list),
        or status: failed and an error message.

    Raises:
        IOError: If loading or saving the metadata file fails after retries.
        ValueError: If the metadata file format is invalid or the key does not exist.
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
                "error": f"Metadata file disappeared for index '{index_name}' during embedding generation.",
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

    if key not in metadata_dict:
        return {
            "status": "failed",
            "error": f"Key '{key}' not found in index '{index_name}'.",
        }

    if not isinstance(metadata_dict[key], dict):
        return {
            "status": "failed",
            "error": f"Metadata for key '{key}' is not a dictionary, cannot add embedding field.",
        }

    # --- Generate Mock Embedding ---
    mock_embedding = np.random.rand(EMBEDDING_DIM).tolist()
    metadata_dict[key]["embedding"] = mock_embedding
    loaded_data["metadata"] = metadata_dict  # Update the structure to be saved

    # --- Save with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)

            print(
                f"Successfully generated and saved embedding for key '{key}' in index '{index_name}'."
            )
            return {
                "status": "success",
                "key": key,
                "embedding_preview": mock_embedding[:3] + ["..."],
            }

        except Exception as e:
            print(
                f"Attempt {attempt + 1} failed to save metadata after generating embedding for '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise OSError(
                    f"Failed to save metadata after generating embedding for '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    return {
        "status": "failed",
        "error": "Unknown error after generating embedding and save attempts.",
    }


# Example usage (for testing purposes)
if __name__ == "__main__":
    from save_metadata_to_faiss_tool import save_metadata_to_faiss

    test_data_emb = {
        "doc_sem1": {"text": "alpha document", "category": "A"},
        "doc_sem2": {"text": "beta document", "category": "B"},
    }
    try:
        print(save_metadata_to_faiss(test_data_emb, "index_semantic_test"))
    except Exception as e:
        print(f"Error saving semantic test data: {e}")

    print("\nGenerating embedding for doc_sem1:")
    try:
        print(generate_embedding("index_semantic_test", "doc_sem1"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nGenerating embedding for non-dict item (should fail):")
    # Need to save a non-dict item first
    try:
        save_metadata_to_faiss({"non_dict_item": "just string"}, "index_temp_non_dict")
        print(generate_embedding("index_temp_non_dict", "non_dict_item"))
    except Exception as e:
        print(f"Expected error: {e}")
