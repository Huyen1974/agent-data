import pickle
import os
import time
from typing import Dict, Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def bulk_update_metadata(index_name: str, filter_condition: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Updates multiple metadata nodes that match a simple filter condition (field == value).

    Args:
        index_name: The name of the FAISS index whose metadata to update.
        filter_condition: A dictionary with one key-value pair defining the filter (e.g., {'project': 'Test'}).
        updates: A dictionary containing the fields and their new values to apply to matching nodes.

    Returns:
        A dictionary with status, count of updated nodes, and optionally an error message.

    Raises:
        IOError: If loading or saving the metadata file fails after retries.
        ValueError: If the metadata file format is invalid or inputs are incorrect.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    index_path = os.path.join(FAISS_DIR, f"{index_name}.faiss")

    if not filter_condition or len(filter_condition) != 1:
        return {"status": "failed", "error": "Filter condition must contain exactly one key-value pair."}
    if not updates:
        return {"status": "failed", "error": "Updates dictionary cannot be empty."}

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
                "error": f"Metadata file disappeared for index '{index_name}' during update attempt.",
            }
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to load metadata for FAISS index '{index_name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise IOError(
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
    updated_count = 0
    updated_keys = []

    # --- Perform Update ---
    for key, item_metadata in metadata_dict.items():
        if isinstance(item_metadata, dict) and item_metadata.get(filter_field) == filter_value:
            item_metadata.update(updates)
            updated_count += 1
            updated_keys.append(key)
            # Ensure the change is reflected in the main dict being saved
            metadata_dict[key] = item_metadata

    if updated_count == 0:
        print(
            f"No nodes matched the filter condition '{filter_condition}' in index '{index_name}'. No updates performed."
        )
        return {"status": "success", "updated_count": 0, "message": "No matching nodes found."}

    loaded_data["metadata"] = metadata_dict

    # --- Save with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)

            print(
                f"Successfully performed bulk update on {updated_count} nodes in index '{index_name}' matching {filter_condition}."
            )
            return {"status": "success", "updated_count": updated_count, "updated_keys": updated_keys}

        except Exception as e:
            print(f"Attempt {attempt + 1} failed to save bulk updated metadata for FAISS index '{index_name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise IOError(
                    f"Failed to save bulk updated metadata for FAISS index '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    return {"status": "failed", "error": "Unknown error after bulk update and save attempts."}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Need test data
    from save_metadata_to_faiss_tool import save_metadata_to_faiss

    test_data_bulk = {
        "item1": {"project": "Test", "status": "draft"},
        "item2": {"project": "Test", "status": "pending"},
        "item3": {"project": "Prod", "status": "approved"},
        "item4": {"project": "Test", "other": "value"},
    }
    try:
        print(save_metadata_to_faiss(test_data_bulk, "index_bulk"))
    except Exception as e:
        print(f"Error saving bulk test data: {e}")

    print("\nBulk updating index_bulk where project='Test' set status='final':")
    try:
        print(bulk_update_metadata("index_bulk", {"project": "Test"}, {"status": "final", "updated": True}))
    except Exception as e:
        print(f"Error: {e}")

    # Verify change
    print("\nVerifying update using load tool:")
    from load_metadata_from_faiss_tool import load_metadata_from_faiss

    try:
        updated_data = load_metadata_from_faiss("index_bulk")
        print(updated_data)
    except Exception as e:
        print(f"Error verifying: {e}")
