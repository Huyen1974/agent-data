import pickle
import os
from typing import Dict, Any

# Reuse or adapt anomaly detection logic
from .detect_anomalies_tool import detect_anomalies as run_anomaly_detection  # Rename for clarity

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def validate_metadata_tree(index_name: str) -> Dict[str, Any]:
    """
    Validates the entire metadata tree in the specified index against predefined rules.
    Currently reuses the anomaly detection logic.

    Args:
        index_name: The name of the FAISS index whose metadata to validate.

    Returns:
        A dictionary containing status: success and the validation results (list of errors/anomalies),
        or status: failed and an error message.

    Raises:
        IOError: If loading the metadata file fails (passed up from detect_anomalies).
        ValueError: If the metadata file format is invalid (passed up from detect_anomalies).
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {"status": "failed", "error": f"Metadata file not found for index '{index_name}'. Cannot validate."}

    try:
        # Reuse the anomaly detection logic for validation
        validation_results = run_anomaly_detection(index_name)

        if validation_results.get("status") == "success":
            validation_summary = {
                "total_nodes_checked": -1,  # Need to load metadata again to get total count
                "issues_found": len(validation_results.get("anomalies", [])),
                "validation_details": validation_results.get("anomalies", []),
            }
            # Add total node count - requires another load, maybe optimize later
            try:
                with open(meta_path, "rb") as f:
                    loaded_data = pickle.load(f)
                if loaded_data and "metadata" in loaded_data:
                    validation_summary["total_nodes_checked"] = len(loaded_data["metadata"])
            except Exception as load_err:
                print(f"Warning: Could not reload metadata to get total count during validation: {load_err}")

            print(f"Validation complete for index '{index_name}'. Issues found: {validation_summary['issues_found']}")
            return {"status": "success", "validation_summary": validation_summary}
        else:
            # Pass through the error from detect_anomalies
            return validation_results

    except (IOError, ValueError) as e:
        # Catch potential errors from the reused function if they weren't handled as dicts
        return {"status": "failed", "error": f"Validation failed due to error in underlying check: {e}"}
    except Exception as e:
        # Catch unexpected errors
        print(f"Unexpected error during validation of index '{index_name}': {e}")
        return {"status": "failed", "error": f"Unexpected validation error: {e}"}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Assumes index_anomalies and index_trends exist

    print("Validating index_anomalies:")
    try:
        print(validate_metadata_tree("index_anomalies"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nValidating index_trends:")
    try:
        print(validate_metadata_tree("index_trends"))
    except Exception as e:
        print(f"Error: {e}")

    print("\nValidating non_existent_index:")
    try:
        print(validate_metadata_tree("non_existent_index"))
    except Exception as e:
        print(f"Error: {e}")
