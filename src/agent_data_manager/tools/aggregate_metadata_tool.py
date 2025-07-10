import pickle
import os
import time
from typing import Dict, Any
from collections import Counter

FAISS_DIR = "faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def aggregate_metadata(index_name: str, aggregate_field: str) -> Dict[str, Any]:
    """
    Loads metadata and aggregates counts based on the values of a specified field.

    Args:
        index_name: The name of the FAISS index whose metadata to aggregate.
        aggregate_field: The field name to group and count by (e.g., 'year', 'type').

    Returns:
        A dictionary with status: success and the aggregated counts, or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {"status": "failed", "error": f"Metadata file not found for index '{index_name}'. Cannot aggregate."}

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
                "error": f"Metadata file disappeared for index '{index_name}' during aggregation attempt.",
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
    aggregation_counts = Counter()
    items_without_field = 0

    for key, value in metadata_dict.items():
        if isinstance(value, dict) and aggregate_field in value:
            field_value = value[aggregate_field]
            # Ensure value is hashable for Counter, convert lists/dicts to tuples/strings if needed?
            # For simple types (str, int, bool, None), it should be fine.
            # Let's convert to string for broad compatibility, though might lose type info.
            try:
                aggregation_counts[str(field_value)] += 1
            except TypeError:
                print(
                    f"Warning: Value '{field_value}' for field '{aggregate_field}' in key '{key}' is not hashable. Skipping."
                )
                items_without_field += 1  # Treat unhashable as missing for aggregation
        else:
            items_without_field += 1

    if not aggregation_counts:
        print(
            f"Warning: No items found with the aggregate field '{aggregate_field}' or no hashable values in index '{index_name}'."
        )
        return {"status": "success", "aggregation": {}, "items_without_field": items_without_field}

    print(f"Successfully aggregated metadata from index '{index_name}' by field '{aggregate_field}'.")
    return {"status": "success", "aggregation": dict(aggregation_counts), "items_without_field": items_without_field}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_trends exists
    print("Aggregating index_trends by 'year':")
    try:
        print(aggregate_metadata("index_trends", "year"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nAggregating index_trends by 'type':")  # Note: Only docB has 'type'
    try:
        print(aggregate_metadata("index_trends", "type"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nAggregating index_trends by missing field 'author':")
    try:
        print(aggregate_metadata("index_trends", "author"))
    except Exception as e:
        print(f"Error: {e}")
