import pickle
import os
import time
from typing import Dict, Any, Optional, Union
from collections import Counter

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def analyze_metadata_trends(
    index_name: str, analysis_type: str, keyword: Optional[str] = None
) -> Dict[str, Union[str, Dict]]:
    """
    Simulates analysis of metadata trends based on specified type.
    Loads metadata and performs analysis like counting items per year or by keyword in a field.

    Args:
        index_name: The name of the FAISS index whose metadata to analyze.
        analysis_type: The type of analysis to perform (e.g., 'by_year', 'by_project_keyword').
        keyword: An optional keyword required for certain analysis types (e.g., for 'by_project_keyword').

    Returns:
        A dictionary containing the analysis results or an error message.

    Raises:
        IOError: If loading the metadata file fails after retries.
        ValueError: If the metadata file format is invalid or input is inconsistent.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not os.path.exists(meta_path):
        return {"error": f"Metadata file not found for index '{index_name}' at {meta_path}. Cannot analyze trends."}

    loaded_data = None
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            return {"error": f"Metadata file disappeared for index '{index_name}' at {meta_path} during analysis."}
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
    results: Dict[str, Any] = Counter()
    analysis_performed = False

    if analysis_type == "by_year":
        for key, item_metadata in metadata_dict.items():
            if isinstance(item_metadata, dict) and "year" in item_metadata:
                year = item_metadata["year"]
                results[str(year)] += 1  # Use string keys for JSON compatibility
            analysis_performed = True  # Mark as performed even if no items had 'year'
    elif analysis_type == "by_project_keyword":
        if not keyword:
            return {"error": "Keyword is required for 'by_project_keyword' analysis type."}
        keyword_lower = keyword.lower()
        for key, item_metadata in metadata_dict.items():
            if isinstance(item_metadata, dict) and "project" in item_metadata:
                project_name = str(item_metadata["project"]).lower()
                if keyword_lower in project_name:
                    # Count occurrences of the keyword across projects
                    # Alternatively, could count projects containing the keyword: results[item_metadata['project']] = 1
                    results["count"] += 1
            analysis_performed = True  # Mark as performed
    else:
        return {
            "error": f"Unsupported analysis type: '{analysis_type}'. Supported types: 'by_year', 'by_project_keyword'"
        }

    if not analysis_performed:
        # This case should ideally not be reached due to checks above, but as a safeguard.
        return {
            "error": f"Analysis type '{analysis_type}' could not be performed (e.g., missing required fields or keyword)."
        }

    if not results:
        print(f"Warning: No matching data found for analysis type '{analysis_type}' in index '{index_name}'.")
        # Return empty counter/dict to indicate no results found for the valid analysis type
        return {"analysis_type": analysis_type, "trends": {}}

    return {"analysis_type": analysis_type, "trends": dict(results)}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Need to save some data with 'year' and 'project' first
    from save_metadata_to_faiss_tool import save_metadata_to_faiss

    test_data_trends = {
        "docA": {"year": 2023, "project": "Project Alpha"},
        "docB": {"year": 2024, "project": "Project Beta", "type": "report"},
        "docC": {"year": 2023, "project": "Data Analysis Alpha"},
        "docD": {"project": "Project Gamma"},  # No year
    }
    try:
        print(save_metadata_to_faiss(test_data_trends, "index_trends"))
    except Exception as e:
        print(f"Error saving test data: {e}")

    print("\nAnalyzing index_trends by year:")
    print(analyze_metadata_trends("index_trends", "by_year"))
    print("\nAnalyzing index_trends by project keyword 'alpha':")
    print(analyze_metadata_trends("index_trends", "by_project_keyword", keyword="alpha"))
    print("\nAnalyzing index_trends by project keyword 'beta':")
    print(analyze_metadata_trends("index_trends", "by_project_keyword", keyword="beta"))
    print("\nAnalyzing index_trends with unsupported type:")
    print(analyze_metadata_trends("index_trends", "by_author"))
    print("\nAnalyzing non_existent_index by year:")
    print(analyze_metadata_trends("non_existent_index", "by_year"))
