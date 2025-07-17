import os
import pickle
import time
from collections import Counter
from typing import Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

DEFAULT_STATS_FIELDS = [
    "year",
    "type",
    "project",
]  # Fields to automatically calculate distribution for


def metadata_statistics(
    index_name: str, fields_to_analyze: list[str] | None = None
) -> dict[str, Any]:
    """
    Calculates basic statistics for the metadata in the specified index.
    Includes total node count and value distributions for specified fields.

    Args:
        index_name: The name of the FAISS index whose metadata to analyze.
        fields_to_analyze: Optional list of field names to get value distributions for.
                           If None, uses DEFAULT_STATS_FIELDS.

    Returns:
        A dictionary with status: success and the calculated statistics, or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for index '{index_name}'. Cannot calculate statistics.",
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
                "error": f"Metadata file disappeared for index '{index_name}' during statistics calculation.",
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
    total_nodes = len(metadata_dict)
    field_distributions = {}

    if fields_to_analyze is None:
        fields_to_analyze = DEFAULT_STATS_FIELDS

    for field in fields_to_analyze:
        counts = Counter()
        missing_count = 0
        for key, value in metadata_dict.items():
            if isinstance(value, dict) and field in value:
                field_value = value[field]
                try:
                    counts[str(field_value)] += 1
                except TypeError:
                    # Treat unhashable values as missing for stats
                    missing_count += 1
            else:
                missing_count += 1
        field_distributions[field] = {
            "value_counts": dict(counts),
            "nodes_missing_field": missing_count,
        }

    print(f"Successfully calculated statistics for index '{index_name}'.")
    return {
        "status": "success",
        "statistics": {
            "total_nodes": total_nodes,
            "field_distributions": field_distributions,
        },
    }


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_trends exists
    print("Calculating statistics for index_trends (default fields):")
    try:
        print(metadata_statistics("index_trends"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nCalculating statistics for index_trends (only 'project' field):")
    try:
        print(metadata_statistics("index_trends", fields_to_analyze=["project"]))
    except Exception as e:
        print(f"Error: {e}")

    # Assumes index_anomalies exists
    print("\nCalculating statistics for index_anomalies:")
    try:
        print(metadata_statistics("index_anomalies"))
    except Exception as e:
        print(f"Error: {e}")
