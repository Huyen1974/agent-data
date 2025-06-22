import pickle
import os
import time
import numpy as np
import faiss  # Needed to rebuild the FAISS index
from typing import Dict, Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def bulk_delete_metadata(index_name: str, filter_condition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deletes multiple metadata nodes that match a simple filter condition (field == value).
    This operation rebuilds the underlying FAISS index and metadata file.

    Args:
        index_name: The name of the FAISS index whose metadata to modify.
        filter_condition: A dictionary with one key-value pair defining the filter (e.g., {'status': 'draft'}).

    Returns:
        A dictionary with status, count of deleted nodes, and optionally an error message.

    Raises:
        IOError: If loading or saving fails after retries.
        ValueError: If the metadata file format is invalid or inputs are incorrect.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    index_path = os.path.join(FAISS_DIR, f"{index_name}.faiss")

    if not filter_condition or len(filter_condition) != 1:
        return {"status": "failed", "error": "Filter condition must contain exactly one key-value pair."}

    filter_field, filter_value = list(filter_condition.items())[0]

    if not os.path.exists(meta_path) or not os.path.exists(index_path):
        return {"status": "failed", "error": f"FAISS index or metadata file not found for '{index_name}'."}

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
                "error": f"Metadata file disappeared for index '{index_name}' during delete attempt.",
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
        raise ValueError(f"Invalid metadata file format for '{index_name}'. Missing 'metadata' key.")

    original_metadata_dict = loaded_data["metadata"]
    metadata_to_keep = {}
    deleted_keys = []

    # --- Filter Data ---
    for key, item_metadata in original_metadata_dict.items():
        if isinstance(item_metadata, dict) and item_metadata.get(filter_field) == filter_value:
            # This item matches the filter, so we delete it (i.e., don't add to metadata_to_keep)
            deleted_keys.append(key)
        else:
            # Keep this item
            metadata_to_keep[key] = item_metadata

    deleted_count = len(deleted_keys)

    if deleted_count == 0:
        print(
            f"No nodes matched the filter condition '{filter_condition}' in index '{index_name}'. No deletions performed."
        )
        return {"status": "success", "deleted_count": 0, "message": "No matching nodes found."}

    # --- Rebuild FAISS Index and Metadata ---
    # Similar logic to save_metadata_to_faiss_tool, but with filtered data
    if not metadata_to_keep:
        # If deletion results in an empty index, remove the files
        try:
            os.remove(index_path)
            os.remove(meta_path)
            print(
                f"Successfully deleted all {deleted_count} matching nodes. Index '{index_name}' is now empty and files removed."
            )
            return {"status": "success", "deleted_count": deleted_count, "remaining_count": 0}
        except OSError as e:
            return {"status": "failed", "error": f"Failed to remove empty index files for '{index_name}': {e}"}

    dimension = 1  # Dummy dimension from save tool
    keys = list(metadata_to_keep.keys())
    num_items = len(keys)
    id_to_key = {i: key for i, key in enumerate(keys)}
    key_to_id = {key: i for i, key in id_to_key.items()}
    ids_to_add = np.array(list(id_to_key.keys()), dtype="int64")
    dummy_vectors = np.zeros((num_items, dimension), dtype="float32")

    new_data_to_save = {"metadata": metadata_to_keep, "id_to_key": id_to_key, "key_to_id": key_to_id}

    # --- Save Rebuilt Index/Metadata with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            # Create and populate the FAISS index
            index_flat = faiss.IndexFlatL2(dimension)
            new_index = faiss.IndexIDMap(index_flat)
            new_index.add_with_ids(dummy_vectors, ids_to_add)
            faiss.write_index(new_index, index_path)

            # Save metadata
            with open(meta_path, "wb") as f:
                pickle.dump(new_data_to_save, f)

            print(
                f"Successfully performed bulk delete on {deleted_count} nodes in index '{index_name}' matching {filter_condition}."
            )
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "remaining_count": num_items,
                "deleted_keys": deleted_keys,
            }

        except Exception as e:
            print(
                f"Attempt {attempt + 1} failed to save rebuilt metadata/index after bulk delete for '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise IOError(
                    f"Failed to save rebuilt index/metadata for '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    return {"status": "failed", "error": "Unknown error after bulk delete and save attempts."}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Use data from bulk_update test
    print("Bulk deleting from index_bulk where status='final':")
    try:
        # Before deletion, items 1, 2, 4 should have status: final
        print(bulk_delete_metadata("index_bulk", {"status": "final"}))
    except Exception as e:
        print(f"Error: {e}")

    # Verify change
    print("\nVerifying deletion using load tool:")
    from load_metadata_from_faiss_tool import load_metadata_from_faiss

    try:
        remaining_data = load_metadata_from_faiss("index_bulk")
        print(remaining_data)
    except Exception as e:
        print(f"Error verifying: {e}")

    # Test deleting non-matching condition
    print("\nAttempting to bulk delete non-matching condition (status='pending'):")
    try:
        print(bulk_delete_metadata("index_bulk", {"status": "pending"}))
    except Exception as e:
        print(f"Error: {e}")
