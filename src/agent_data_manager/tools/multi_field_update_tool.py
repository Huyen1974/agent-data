import os
import pickle
import time
from typing import Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def multi_field_update(
    index_name: str, key: str, updates: dict[str, Any]
) -> dict[str, Any]:
    """
    Updates multiple fields of a specific metadata node (identified by key)
    within the specified FAISS index's companion metadata file.

    Args:
        index_name: The name of the FAISS index whose metadata to update.
        key: The key of the metadata node to update.
        updates: A dictionary containing the fields and their new values to update.

    Returns:
        A dictionary with status: success and the updated metadata, or status: failed and an error message.

    Raises:
        IOError: If loading or saving the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    index_path = os.path.join(FAISS_DIR, f"{index_name}.faiss")  # Check for consistency

    if not updates:
        return {"status": "failed", "error": "Updates dictionary cannot be empty."}

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
                "error": f"Metadata file disappeared for index '{index_name}' during update attempt.",
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
            "error": f"Metadata for key '{key}' is not a dictionary, cannot update fields.",
        }

    # --- Perform Update ---
    metadata_dict[key].update(updates)
    loaded_data["metadata"] = (
        metadata_dict  # Ensure the loaded data reflects the change
    )

    # --- Save with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)

            # Optionally: Reload to confirm save? For now, assume success.
            print(
                f"Successfully updated fields for key '{key}' in index '{index_name}'."
            )
            return {"status": "success", "updated_metadata": metadata_dict[key]}

        except Exception as e:
            print(
                f"Attempt {attempt + 1} failed to save updated metadata for FAISS index '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                # Attempt to restore original state? Difficult without transactionality.
                # For now, raise error indicating save failure.
                raise OSError(
                    f"Failed to save updated metadata for FAISS index '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    # Should not be reached if save loop works correctly
    return {
        "status": "failed",
        "error": "Unknown error after update and save attempts.",
    }


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_trends exists
    print(
        "Updating index_trends, key 'docB' with {'status': 'final', 'reviewed': True}:"
    )
    try:
        print(
            multi_field_update(
                "index_trends", "docB", {"status": "final", "reviewed": True}
            )
        )
    except Exception as e:
        print(f"Error: {e}")

    # Verify change (using query tool if available, or load tool)
    print("\nVerifying update using load tool:")
    from load_metadata_from_faiss_tool import load_metadata_from_faiss

    try:
        updated_data = load_metadata_from_faiss("index_trends")
        print(updated_data.get("docB"))
    except Exception as e:
        print(f"Error verifying: {e}")

    print("\nAttempting to update non-existent key:")
    try:
        print(multi_field_update("index_trends", "docZ", {"status": "new"}))
    except Exception as e:
        print(f"Error: {e}")
