import pickle
import os
import time
from typing import Dict, Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def sort_metadata(index_name: str, sort_field: str, ascending: bool = True) -> Dict[str, Any]:
    """
    Loads metadata from the specified FAISS index's companion file and sorts
    the entries based on the value of a specified field.

    Args:
        index_name: The name of the FAISS index whose metadata to sort.
        sort_field: The name of the field within the metadata values to sort by.
        ascending: Whether to sort in ascending order (default: True).

    Returns:
        A dictionary containing status: success and the sorted list of metadata entries (key-value pairs),
        or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {"status": "failed", "error": f"Metadata file not found for index '{index_name}'. Cannot sort."}

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
                "error": f"Metadata file disappeared for index '{index_name}' during sort attempt.",
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
    items_to_sort = []
    items_with_missing_key = []

    # Separate items with and without the sort key
    for key, value in metadata_dict.items():
        if isinstance(value, dict) and sort_field in value:
            items_to_sort.append((key, value))
        else:
            items_with_missing_key.append((key, value))

    if not items_to_sort:
        print(f"Warning: No items found with the sort field '{sort_field}' in index '{index_name}'.")
        # Return all items unsorted, potentially?
        # Or return empty sorted list + unsorted list?
        # Let's return success but indicate nothing was sorted.
        return {"status": "success", "sorted_items": [], "items_without_sort_key": items_with_missing_key}

    # --- Perform Sort ---
    try:
        # Attempt to sort. This might fail if types are incompatible.
        sorted_items = sorted(items_to_sort, key=lambda item: item[1][sort_field], reverse=not ascending)
    except TypeError as e:
        return {
            "status": "failed",
            "error": f"Could not sort by field '{sort_field}': Incompatible data types found. Error: {e}",
        }
    except Exception as e:
        # Catch other potential sorting errors
        return {"status": "failed", "error": f"An unexpected error occurred during sorting: {e}"}

    print(f"Successfully sorted metadata from index '{index_name}' by field '{sort_field}'.")
    return {"status": "success", "sorted_items": sorted_items, "items_without_sort_key": items_with_missing_key}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_trends exists
    print("Sorting index_trends by 'year' ascending:")
    try:
        print(sort_metadata("index_trends", "year", ascending=True))
    except Exception as e:
        print(f"Error: {e}")

    print("\nSorting index_trends by 'project' descending:")
    try:
        print(sort_metadata("index_trends", "project", ascending=False))
    except Exception as e:
        print(f"Error: {e}")

    print("\nSorting index_trends by missing field 'status':")
    try:
        print(sort_metadata("index_trends", "status"))
    except Exception as e:
        print(f"Error: {e}")

    # Example with potentially mixed types (if data had it)
    # print("\nSorting index_trends by potentially mixed type field 'value':")
    # try:
    #     print(sort_metadata('index_trends', 'value'))
    # except Exception as e:
    #     print(f"Error: {e}")
