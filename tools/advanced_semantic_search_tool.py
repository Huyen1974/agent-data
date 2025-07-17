import os
import pickle
import time
from typing import Any


# Assuming helper from semantic_filter_metadata_tool is available or redefined here
# Let's redefine it for clarity and self-containment
def _check_values_contain_keywords(data: Any, keywords: list[str]) -> bool:
    """Recursively check if any string value contains any of the keywords (case-insensitive)."""
    if not keywords:  # Optimization: If no keywords, no need to search
        return True  # Or False depending on desired logic? Let's say True (no keyword restriction)
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
    return False


FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def advanced_semantic_search(
    index_name: str,
    structured_criteria: dict[str, Any] | None = None,
    semantic_keywords: list[str] | None = None,
) -> dict[str, Any]:
    """
    Performs an advanced search combining structured field criteria and semantic keyword matching.
    Loads metadata, filters by structured criteria first, then by semantic keywords.

    Args:
        index_name: The name of the FAISS index whose metadata to search.
        structured_criteria: Optional dictionary for structured field matching (key=value).
        semantic_keywords: Optional list of keywords for semantic matching within values.

    Returns:
        A dictionary containing status: success and the list of matching metadata entries (key-value pairs),
        or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not structured_criteria and not semantic_keywords:
        return {
            "status": "failed",
            "error": "At least one search criteria (structured or semantic) must be provided.",
        }

    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for index '{index_name}'. Cannot search.",
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
                "error": f"Metadata file disappeared for index '{index_name}' during search attempt.",
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

    if loaded_data is None or "metadata" not in loaded_data:
        raise ValueError(f"Invalid metadata file format for '{index_name}'.")

    metadata_dict = loaded_data["metadata"]
    intermediate_results = []

    # --- Stage 1: Structured Criteria Filter ---
    if structured_criteria:
        for key, item_metadata in metadata_dict.items():
            if not isinstance(item_metadata, dict):
                continue
            match = True
            for crit_key, crit_value in structured_criteria.items():
                if (
                    crit_key not in item_metadata
                    or item_metadata[crit_key] != crit_value
                ):
                    match = False
                    break
            if match:
                intermediate_results.append((key, item_metadata))
    else:
        # If no structured criteria, all items pass to the next stage
        intermediate_results = list(metadata_dict.items())

    if not intermediate_results:
        print(
            "No items matched structured criteria (or no structured criteria provided)."
        )
        return {"status": "success", "matching_items": []}

    # --- Stage 2: Semantic Keyword Filter ---
    final_results = []
    if semantic_keywords:
        # Filter the intermediate results further
        for key, item_metadata in intermediate_results:
            if _check_values_contain_keywords(item_metadata, semantic_keywords):
                final_results.append({key: item_metadata})  # Return as list of dicts
    else:
        # If no semantic keywords, all intermediate results are final results
        final_results = [{key: value} for key, value in intermediate_results]

    if not final_results:
        print(
            f"No items matching criteria found in index '{index_name}'. Criteria: structured={structured_criteria}, semantic={semantic_keywords}"
        )

    return {"status": "success", "matching_items": final_results}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_trends exists
    print("Searching index_trends: structured={'year': 2023}, semantic=['alpha']")
    try:
        print(
            advanced_semantic_search(
                "index_trends",
                structured_criteria={"year": 2023},
                semantic_keywords=["alpha"],
            )
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\nSearching index_trends: structured={'type': 'report'}")
    try:
        print(
            advanced_semantic_search(
                "index_trends", structured_criteria={"type": "report"}
            )
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\nSearching index_trends: semantic=['gamma']")
    try:
        print(advanced_semantic_search("index_trends", semantic_keywords=["gamma"]))
    except Exception as e:
        print(f"Error: {e}")

    print(
        "\nSearching index_trends: structured={'year': 2024}, semantic=['alpha'] (no match expected)"
    )
    try:
        print(
            advanced_semantic_search(
                "index_trends",
                structured_criteria={"year": 2024},
                semantic_keywords=["alpha"],
            )
        )
    except Exception as e:
        print(f"Error: {e}")

    print("\nSearching index_trends: No criteria (should fail)")
    try:
        print(advanced_semantic_search("index_trends"))
    except Exception as e:
        print(f"Error: {e}")
