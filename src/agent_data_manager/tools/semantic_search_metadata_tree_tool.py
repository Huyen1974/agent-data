import pickle
import os
import time
from typing import Dict, Any, List

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def _search_dict_values(data: Any, query: str) -> bool:
    """Recursively search for query string in dictionary values or list elements."""
    if isinstance(data, dict):
        for value in data.values():
            if _search_dict_values(value, query):
                return True
    elif isinstance(data, list):
        for item in data:
            if _search_dict_values(item, query):
                return True
    elif isinstance(data, str):
        return query.lower() in data.lower()
    return False


def semantic_search_metadata_tree(index_name: str, query: str) -> List[Dict[str, Any]]:
    """
    Simulates semantic search by performing keyword search within the metadata values
    loaded from the specified FAISS index's companion file.

    Args:
        index_name: The name of the FAISS index whose metadata to search.
        query: The keyword/query string to search for within metadata values.

    Returns:
        A list of metadata entries (key-value pairs) where the query was found in the value.
        Returns an empty list if the index is not found or the query yields no results.

    Raises:
        IOError: If loading fails after retries.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    results = []

    if not os.path.exists(meta_path):
        print(f"Warning: Metadata file not found for index '{index_name}' at {meta_path}. Cannot perform search.")
        return []  # Return empty list as per requirement

    loaded_data = None
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            print(f"Warning: Metadata file disappeared for index '{index_name}' at {meta_path} during search.")
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

    for key, value in metadata_dict.items():
        if _search_dict_values(value, query):
            results.append({key: value})

    if not results:
        print(f"Query '{query}' did not match any metadata values in index '{index_name}'.")

    return results


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_v1 and index_v2 exist from previous steps
    print("Searching index_v1 for 'final':")
    print(semantic_search_metadata_tree("index_v1", "final"))
    print("\\nSearching index_v1 for 'summary':")
    print(semantic_search_metadata_tree("index_v1", "summary"))
    print("\\nSearching index_v2 for 'draft':")
    print(semantic_search_metadata_tree("index_v2", "draft"))
    print("\\nSearching index_v1 for 'nonexistent':")
    print(semantic_search_metadata_tree("index_v1", "nonexistent"))
    print("\\nSearching non_existent_index for 'test':")
    print(semantic_search_metadata_tree("non_existent_index", "test"))
