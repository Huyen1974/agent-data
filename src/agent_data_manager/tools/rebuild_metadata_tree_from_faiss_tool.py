import os
import pickle
import time
from typing import Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def rebuild_metadata_tree_from_faiss(index_name: str) -> dict[str, Any]:
    """
    Rebuilds (loads) the metadata tree structure from the specified FAISS index's companion file.
    This is functionally equivalent to loading the metadata.

    Args:
        index_name: The name of the FAISS index whose metadata to load.

    Returns:
        The loaded metadata dictionary representing the tree structure.
        Returns an empty dictionary if the index is not found.

    Raises:
        IOError: If loading fails after retries.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        # Check associated .faiss file too for consistency, though we don't load it
        index_path = os.path.join(FAISS_DIR, f"{index_name}.faiss")
        if not os.path.exists(index_path):
            print(
                f"Warning: FAISS index file AND metadata file not found for '{index_name}' in {FAISS_DIR}. Cannot rebuild tree."
            )
        else:
            print(
                f"Warning: Metadata file (.meta) not found for index '{index_name}' at {meta_path}, although .faiss file exists. Cannot rebuild tree."
            )
        return {}  # Return empty dict as per requirement

    loaded_data = None
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            # This case might happen if file deleted between os.path.exists and open
            print(
                f"Warning: Metadata file disappeared for index '{index_name}' at {meta_path} during rebuild."
            )
            return {}
        except Exception as e:
            print(
                f"Attempt {attempt + 1} failed to load metadata for FAISS index '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                # Raise error after retries fail
                raise OSError(
                    f"Failed to load metadata for FAISS index '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    if loaded_data is None or "metadata" not in loaded_data:
        print(
            f"Warning: Invalid or empty metadata file format for '{index_name}'. Returning empty tree."
        )
        return {}

    print(f"Successfully rebuilt metadata tree from index '{index_name}'.")
    return loaded_data["metadata"]


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_v1 and index_v2 exist
    print("Rebuilding from index_v1:")
    tree1 = rebuild_metadata_tree_from_faiss("index_v1")
    print(tree1)
    print("\nRebuilding from index_v2:")
    tree2 = rebuild_metadata_tree_from_faiss("index_v2")
    print(tree2)
    print("\nRebuilding from non_existent_index:")
    tree3 = rebuild_metadata_tree_from_faiss("non_existent_index")
    print(tree3)
