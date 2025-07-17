import os
import pickle
import time
from typing import Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def _check_values_contain_keywords(data: Any, keywords: list[str]) -> bool:
    """Recursively check if any string value contains any of the keywords (case-insensitive)."""
    if isinstance(data, dict):
        for value in data.values():
            if _check_values_contain_keywords(value, keywords):
                return True
    elif isinstance(data, list):
        for item in data:
            if _check_values_contain_keywords(item, keywords):
                return True
    elif isinstance(data, str):
        data_lower = data.lower()
        for keyword in keywords:
            if keyword.lower() in data_lower:
                return True
    # Consider other types like numbers? For now, only strings.
    return False


def semantic_filter_metadata(
    index_name: str, semantic_criteria: list[str]
) -> list[dict[str, Any]]:
    """
    Simulates semantic filtering of metadata based on a list of keywords.
    Loads metadata and returns entries where any value contains any of the criteria keywords.

    Args:
        index_name: The name of the FAISS index whose metadata to filter.
        semantic_criteria: A list of keywords to filter by.

    Returns:
        A list of metadata entries (key-value pairs) that match the criteria.
        Returns an empty list if the index is not found or no entries match.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")
    results = []

    if not semantic_criteria:
        print("Warning: Empty semantic criteria provided for filtering.")
        return []

    if not os.path.exists(meta_path):
        print(
            f"Warning: Metadata file not found for index '{index_name}' at {meta_path}. Cannot filter."
        )
        return []

    loaded_data = None
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            print(
                f"Warning: Metadata file disappeared for index '{index_name}' at {meta_path} during filter."
            )
            return []
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

    if loaded_data is None or "metadata" not in loaded_data:
        raise ValueError(
            f"Invalid metadata file format for '{index_name}'. Missing 'metadata' key."
        )

    metadata_dict = loaded_data["metadata"]

    for key, value in metadata_dict.items():
        if _check_values_contain_keywords(value, semantic_criteria):
            results.append({key: value})

    if not results:
        print(
            f"No metadata entries in index '{index_name}' matched semantic criteria: {semantic_criteria}"
        )

    return results


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_v1 and index_v2 exist
    print("Filtering index_v1 for ['final', 'report']:")
    print(semantic_filter_metadata("index_v1", ["final", "report"]))
    print("\nFiltering index_v1 for ['summary']:")
    print(semantic_filter_metadata("index_v1", ["summary"]))
    print("\nFiltering index_v2 for ['project']:")
    print(semantic_filter_metadata("index_v2", ["project"]))
    print("\nFiltering index_v1 for ['nonexistent', 'keyword']:")
    print(semantic_filter_metadata("index_v1", ["nonexistent", "keyword"]))
    print("\nFiltering non_existent_index for ['test']:")
    print(semantic_filter_metadata("non_existent_index", ["test"]))
