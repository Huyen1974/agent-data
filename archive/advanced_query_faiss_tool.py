import pickle
import os
import time
from typing import Dict, Any, List

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def advanced_query_faiss(index_name: str, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Queries the metadata loaded from the specified FAISS index's companion file
    based on multiple field criteria.

    Args:
        index_name: The name of the FAISS index whose metadata to query.
        criteria: A dictionary where keys are metadata field names and values are
                  the desired values for those fields.

    Returns:
        A list of metadata entries (key-value pairs) that match ALL criteria.
        Returns an empty list if the index is not found or no entries match.

    Raises:
        IOError: If loading fails after retries.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    results = []

    if not criteria:
        print("Warning: Empty criteria provided for advanced query.")
        return []

    if not os.path.exists(meta_path):
        print(f"Warning: Metadata file not found for index '{index_name}' at {meta_path}. Cannot perform query.")
        return []  # Return empty list as per requirement

    loaded_data = None
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            print(f"Warning: Metadata file disappeared for index '{index_name}' at {meta_path} during query.")
            return []  # File gone, return empty
        except Exception as e:
            print(f"Attempt {attempt + 1} failed to load metadata for FAISS index '{index_name}': {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                # Raise error after retries fail for loading issues other than FileNotFoundError
                raise IOError(
                    f"Failed to load metadata for FAISS index '{index_name}' after {MAX_RETRIES} attempts."
                ) from e

    if loaded_data is None or "metadata" not in loaded_data:
        print(f"Warning: Invalid or empty metadata file format for '{index_name}'.")
        return []

    metadata_dict = loaded_data["metadata"]

    for key, item_metadata in metadata_dict.items():
        if not isinstance(item_metadata, dict):
            continue  # Skip items whose metadata isn't a dictionary

        match = True
        for crit_key, crit_value in criteria.items():
            if crit_key not in item_metadata or item_metadata[crit_key] != crit_value:
                match = False
                break

        if match:
            results.append({key: item_metadata})

    if not results:
        print(f"No metadata entries in index '{index_name}' matched all criteria: {criteria}")

    return results


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_v1 and index_v2 exist
    print("Querying index_v1 for {'author': 'A', 'status': 'final'}:")
    print(advanced_query_faiss("index_v1", {"author": "A", "status": "final"}))
    print("\\nQuerying index_v1 for {'type': 'summary'}:")
    print(advanced_query_faiss("index_v1", {"type": "summary"}))
    print("\\nQuerying index_v2 for {'project': 'X'}:")
    print(advanced_query_faiss("index_v2", {"project": "X"}))
    print("\\nQuerying index_v1 for {'author': 'A', 'status': 'draft'} (should be empty):")
    print(advanced_query_faiss("index_v1", {"author": "A", "status": "draft"}))
    print("\\nQuerying non_existent_index for {'a': 1}:")
    print(advanced_query_faiss("non_existent_index", {"a": 1}))
