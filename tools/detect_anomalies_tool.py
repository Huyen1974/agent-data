import pickle
import os
import time
from typing import Dict, Any

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# --- Anomaly Detection Rules ---
MIN_YEAR = 1900
MAX_YEAR = 2100  # Adjust as needed
REQUIRED_FIELDS = ["project"]  # Example required field


def detect_anomalies(index_name: str) -> Dict[str, Any]:
    """
    Loads metadata and detects predefined anomalies in the values.
    Checks for: year out of range, missing required fields.

    Args:
        index_name: The name of the FAISS index whose metadata to check.

    Returns:
        A dictionary with status: success and a list of detected anomalies (key and reason),
        or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for index '{index_name}'. Cannot detect anomalies.",
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
                "error": f"Metadata file disappeared for index '{index_name}' during anomaly detection.",
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
    anomalies_found = []

    for key, value in metadata_dict.items():
        if not isinstance(value, dict):
            anomalies_found.append({"key": key, "reason": "Metadata value is not a dictionary."})
            continue

        # Check year range
        if "year" in value:
            try:
                year = int(value["year"])
                if not (MIN_YEAR <= year <= MAX_YEAR):
                    anomalies_found.append(
                        {
                            "key": key,
                            "field": "year",
                            "value": year,
                            "reason": f"Year out of range ({MIN_YEAR}-{MAX_YEAR}).",
                        }
                    )
            except (ValueError, TypeError):
                anomalies_found.append(
                    {
                        "key": key,
                        "field": "year",
                        "value": value["year"],
                        "reason": "Year value is not a valid integer.",
                    }
                )

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in value or not value[field]:  # Check for presence and non-empty
                anomalies_found.append(
                    {"key": key, "field": field, "reason": f"Required field '{field}' is missing or empty."}
                )

    if not anomalies_found:
        print(f"No anomalies detected in index '{index_name}' based on current rules.")

    return {"status": "success", "anomalies": anomalies_found}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Create test data with anomalies
    from save_metadata_to_faiss_tool import save_metadata_to_faiss

    test_data_anomalies = {
        "doc_ok": {"year": 2020, "project": "Good Project"},
        "doc_bad_year": {"year": 1850, "project": "Old Project"},
        "doc_missing_proj": {"year": 2021},
        "doc_str_year": {"year": "Two Thousand Twenty Two", "project": "String Year Project"},
        "doc_non_dict": "Just a string",
    }
    try:
        print(save_metadata_to_faiss(test_data_anomalies, "index_anomalies"))
    except Exception as e:
        print(f"Error saving anomaly test data: {e}")

    print("\nDetecting anomalies in index_anomalies:")
    try:
        print(detect_anomalies("index_anomalies"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nDetecting anomalies in index_trends (should be none based on rules):")
    try:
        print(detect_anomalies("index_trends"))
    except Exception as e:
        print(f"Error: {e}")
