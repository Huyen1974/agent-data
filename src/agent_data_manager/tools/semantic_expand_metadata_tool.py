import pickle
import os
import time
from typing import Dict, Any, Optional

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def semantic_expand_metadata(index_name: str, keyword: str) -> Optional[Dict[str, Any]]:
    """
    Simulates semantic expansion for a metadata node identified by a keyword.
    Loads the metadata, finds the entry for the keyword, and adds simulated related keywords.

    Args:
        index_name: The name of the FAISS index whose metadata to use.
        keyword: The key identifying the metadata node to expand.

    Returns:
        The original metadata for the keyword with an added 'simulated_expansion' field,
        or None if the index or keyword is not found.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        print(f"Warning: Metadata file not found for index '{index_name}' at {meta_path}. Cannot expand.")
        return None

    loaded_data = None
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            print(f"Warning: Metadata file disappeared for index '{index_name}' at {meta_path} during expansion.")
            return None
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

    metadata_dict = loaded_data["metadata"]

    if keyword in metadata_dict:
        original_metadata = metadata_dict[keyword]
        # Simulate semantic expansion
        simulated_related = [f"{keyword}_related_term_1", f"{keyword}_topic_A", "generic_concept"]
        # Avoid modifying the original dict directly if loaded elsewhere
        expanded_metadata = (
            original_metadata.copy() if isinstance(original_metadata, dict) else {"value": original_metadata}
        )
        expanded_metadata["simulated_expansion"] = simulated_related
        return expanded_metadata
    else:
        print(f"Warning: Keyword '{keyword}' not found in index '{index_name}'. Cannot expand.")
        return None


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_v1 and index_v2 exist
    print("Expanding index_v1 for 'doc001':")
    print(semantic_expand_metadata("index_v1", "doc001"))
    print("\nExpanding index_v2 for 'doc002':")
    print(semantic_expand_metadata("index_v2", "doc002"))
    print("\nExpanding index_v1 for 'nonexistent':")
    print(semantic_expand_metadata("index_v1", "nonexistent"))
    print("\nExpanding non_existent_index for 'doc001':")
    print(semantic_expand_metadata("non_existent_index", "doc001"))
