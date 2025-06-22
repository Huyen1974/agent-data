"""
Cloud Function for automated change reporting triggered by Firestore document changes.
Generates JSON reports of data changes and stores them in Firestore or GCS.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

import functions_framework
from google.cloud import firestore
from google.cloud import storage
from google.cloud.functions_v1 import CloudEvent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "chatgpt-db-project"
REPORTS_COLLECTION = "change_reports"
GCS_BUCKET = "agent-data-storage-test"
REPORT_STORAGE_MODE = "firestore"  # Options: "firestore", "gcs", "both"


def initialize_clients():
    """Initialize Firestore and GCS clients."""
    try:
        firestore_client = firestore.Client(project=PROJECT_ID)
        storage_client = storage.Client(project=PROJECT_ID)
        return firestore_client, storage_client
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        raise


def extract_change_info(cloud_event: CloudEvent) -> Dict[str, Any]:
    """
    Extract change information from Firestore CloudEvent.

    Args:
        cloud_event: CloudEvent from Firestore trigger

    Returns:
        Dictionary with change information
    """
    try:
        # Extract event data
        event_data = cloud_event.data
        event_type = cloud_event.get("eventType", "unknown")

        # Parse document path
        resource_name = event_data.get("value", {}).get("name", "")
        path_parts = resource_name.split("/")

        if len(path_parts) >= 6:
            collection_name = path_parts[-3]
            document_id = path_parts[-1]
        else:
            collection_name = "unknown"
            document_id = "unknown"

        # Extract old and new values
        old_value = event_data.get("oldValue", {}).get("fields", {})
        new_value = event_data.get("value", {}).get("fields", {})

        # Determine operation type
        operation_type = "unknown"
        if event_type.endswith("created"):
            operation_type = "create"
        elif event_type.endswith("updated"):
            operation_type = "update"
        elif event_type.endswith("deleted"):
            operation_type = "delete"

        return {
            "event_type": event_type,
            "operation_type": operation_type,
            "collection": collection_name,
            "document_id": document_id,
            "old_value": old_value,
            "new_value": new_value,
            "resource_name": resource_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to extract change info: {e}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


def analyze_changes(old_value: Dict[str, Any], new_value: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze changes between old and new document values with enhanced analytics.

    Args:
        old_value: Previous document fields
        new_value: Current document fields

    Returns:
        Comprehensive analysis of changes
    """
    changes = {
        "added_fields": [],
        "modified_fields": [],
        "removed_fields": [],
        "field_count_change": 0,
        "significant_changes": [],
        "impact_analysis": {},
        "change_frequency": {},
        "data_quality_metrics": {},
    }

    try:
        # Convert Firestore field format to simple values
        old_simple = convert_firestore_fields(old_value)
        new_simple = convert_firestore_fields(new_value)

        # Find added fields
        for field in new_simple:
            if field not in old_simple:
                changes["added_fields"].append(
                    {"field": field, "value": new_simple[field], "type": type(new_simple[field]).__name__}
                )

        # Find removed fields
        for field in old_simple:
            if field not in new_simple:
                changes["removed_fields"].append(
                    {"field": field, "old_value": old_simple[field], "type": type(old_simple[field]).__name__}
                )

        # Find modified fields with detailed analysis
        for field in new_simple:
            if field in old_simple and old_simple[field] != new_simple[field]:
                change_detail = {
                    "field": field,
                    "old_value": old_simple[field],
                    "new_value": new_simple[field],
                    "old_type": type(old_simple[field]).__name__,
                    "new_type": type(new_simple[field]).__name__,
                    "change_type": "value_change",
                }

                # Detect type changes
                if not isinstance(old_simple[field], type(new_simple[field])):
                    change_detail["change_type"] = "type_change"

                # Analyze string changes
                if isinstance(old_simple[field], str) and isinstance(new_simple[field], str):
                    change_detail["length_change"] = len(new_simple[field]) - len(old_simple[field])
                    change_detail["similarity"] = calculate_string_similarity(old_simple[field], new_simple[field])

                # Analyze numeric changes
                if isinstance(old_simple[field], (int, float)) and isinstance(new_simple[field], (int, float)):
                    change_detail["numeric_change"] = new_simple[field] - old_simple[field]
                    change_detail["percent_change"] = (
                        ((new_simple[field] - old_simple[field]) / old_simple[field] * 100)
                        if old_simple[field] != 0
                        else 0
                    )

                changes["modified_fields"].append(change_detail)

        # Calculate field count change
        changes["field_count_change"] = len(new_simple) - len(old_simple)

        # Enhanced significant changes analysis
        significant_fields = {
            "vectorStatus": "critical",
            "version": "high",
            "tags": "medium",
            "auto_tags": "medium",
            "level_1": "high",
            "level_2": "medium",
            "level_3": "medium",
            "lastUpdated": "low",
            "original_text": "critical",
        }

        for change in changes["modified_fields"]:
            field = change["field"]
            if field in significant_fields:
                changes["significant_changes"].append(
                    {"field": field, "importance": significant_fields[field], "change_type": change["change_type"]}
                )

        # Impact analysis
        changes["impact_analysis"] = analyze_change_impact(old_simple, new_simple, changes)

        # Data quality metrics
        changes["data_quality_metrics"] = calculate_data_quality_metrics(old_simple, new_simple)

        return changes

    except Exception as e:
        logger.error(f"Failed to analyze changes: {e}")
        return {"error": str(e)}


def calculate_string_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings using simple character overlap."""
    if not str1 or not str2:
        return 0.0

    set1 = set(str1.lower())
    set2 = set(str2.lower())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


def analyze_change_impact(
    old_data: Dict[str, Any], new_data: Dict[str, Any], changes: Dict[str, Any]
) -> Dict[str, Any]:
    """Analyze the impact of changes on the document and system."""
    impact = {"overall_impact": "low", "affected_systems": [], "workflow_impact": [], "data_integrity_risk": "low"}

    # Determine overall impact based on significant changes
    critical_changes = [c for c in changes.get("significant_changes", []) if c.get("importance") == "critical"]
    high_changes = [c for c in changes.get("significant_changes", []) if c.get("importance") == "high"]

    if critical_changes:
        impact["overall_impact"] = "critical"
    elif high_changes:
        impact["overall_impact"] = "high"
    elif changes.get("significant_changes"):
        impact["overall_impact"] = "medium"

    # Identify affected systems
    if any(c["field"] == "vectorStatus" for c in changes.get("modified_fields", [])):
        impact["affected_systems"].append("vector_search")

    if any(c["field"].startswith("level_") for c in changes.get("modified_fields", [])):
        impact["affected_systems"].append("hierarchy_navigation")

    if any(c["field"] in ["tags", "auto_tags"] for c in changes.get("modified_fields", [])):
        impact["affected_systems"].append("tagging_system")

    # Workflow impact analysis
    if old_data.get("vectorStatus") == "pending" and new_data.get("vectorStatus") == "completed":
        impact["workflow_impact"].append("vectorization_completed")

    if old_data.get("vectorStatus") == "completed" and new_data.get("vectorStatus") == "failed":
        impact["workflow_impact"].append("vectorization_failed")
        impact["data_integrity_risk"] = "high"

    return impact


def calculate_data_quality_metrics(old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate data quality metrics for the change."""
    metrics = {"completeness_score": 0.0, "consistency_score": 0.0, "validity_score": 0.0, "quality_trend": "stable"}

    # Calculate completeness (percentage of non-null fields)
    total_fields = len(new_data)
    non_null_fields = sum(1 for v in new_data.values() if v is not None and v != "")
    metrics["completeness_score"] = non_null_fields / total_fields if total_fields > 0 else 0.0

    # Calculate consistency (hierarchy levels properly filled)
    hierarchy_fields = ["level_1", "level_2", "level_3", "level_4", "level_5", "level_6"]
    hierarchy_consistency = 0
    for i, field in enumerate(hierarchy_fields):
        if field in new_data and new_data[field]:
            hierarchy_consistency = i + 1
        else:
            break
    metrics["consistency_score"] = hierarchy_consistency / len(hierarchy_fields)

    # Calculate validity (required fields present and properly formatted)
    required_fields = ["doc_id", "vectorStatus", "lastUpdated"]
    valid_fields = sum(1 for field in required_fields if field in new_data and new_data[field])
    metrics["validity_score"] = valid_fields / len(required_fields)

    # Determine quality trend
    old_completeness = (
        len([v for v in old_data.values() if v is not None and v != ""]) / len(old_data) if old_data else 0
    )
    if metrics["completeness_score"] > old_completeness:
        metrics["quality_trend"] = "improving"
    elif metrics["completeness_score"] < old_completeness:
        metrics["quality_trend"] = "declining"

    return metrics


def convert_firestore_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Firestore field format to simple key-value pairs.

    Args:
        fields: Firestore fields dictionary

    Returns:
        Simplified dictionary
    """
    simple_dict = {}

    for field_name, field_value in fields.items():
        if isinstance(field_value, dict):
            # Extract value based on Firestore type
            if "stringValue" in field_value:
                simple_dict[field_name] = field_value["stringValue"]
            elif "integerValue" in field_value:
                simple_dict[field_name] = int(field_value["integerValue"])
            elif "doubleValue" in field_value:
                simple_dict[field_name] = float(field_value["doubleValue"])
            elif "booleanValue" in field_value:
                simple_dict[field_name] = field_value["booleanValue"]
            elif "timestampValue" in field_value:
                simple_dict[field_name] = field_value["timestampValue"]
            elif "arrayValue" in field_value:
                simple_dict[field_name] = field_value["arrayValue"].get("values", [])
            elif "mapValue" in field_value:
                simple_dict[field_name] = convert_firestore_fields(field_value["mapValue"].get("fields", {}))
            else:
                simple_dict[field_name] = str(field_value)
        else:
            simple_dict[field_name] = field_value

    return simple_dict


def generate_change_report(change_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a comprehensive change report.

    Args:
        change_info: Change information extracted from CloudEvent

    Returns:
        Complete change report
    """
    report = {
        "report_id": f"change_{change_info['document_id']}_{int(datetime.utcnow().timestamp())}",
        "generated_at": datetime.utcnow().isoformat(),
        "event_info": {
            "event_type": change_info["event_type"],
            "operation_type": change_info["operation_type"],
            "collection": change_info["collection"],
            "document_id": change_info["document_id"],
            "timestamp": change_info["timestamp"],
        },
        "changes": {},
        "metadata": {"function_name": "change_report_function", "version": "1.0.0", "project_id": PROJECT_ID},
    }

    # Add change analysis for update operations
    if change_info["operation_type"] == "update":
        report["changes"] = analyze_changes(change_info["old_value"], change_info["new_value"])
    elif change_info["operation_type"] == "create":
        report["changes"] = {
            "operation": "document_created",
            "field_count": len(change_info["new_value"]),
            "fields": list(convert_firestore_fields(change_info["new_value"]).keys()),
        }
    elif change_info["operation_type"] == "delete":
        report["changes"] = {
            "operation": "document_deleted",
            "field_count": len(change_info["old_value"]),
            "fields": list(convert_firestore_fields(change_info["old_value"]).keys()),
        }

    return report


def store_report_firestore(report: Dict[str, Any], firestore_client) -> bool:
    """
    Store change report in Firestore.

    Args:
        report: Change report to store
        firestore_client: Firestore client

    Returns:
        Success status
    """
    try:
        doc_ref = firestore_client.collection(REPORTS_COLLECTION).document(report["report_id"])
        doc_ref.set(report)
        logger.info(f"Stored change report in Firestore: {report['report_id']}")
        return True
    except Exception as e:
        logger.error(f"Failed to store report in Firestore: {e}")
        return False


def store_report_gcs(report: Dict[str, Any], storage_client) -> bool:
    """
    Store change report in Google Cloud Storage.

    Args:
        report: Change report to store
        storage_client: GCS client

    Returns:
        Success status
    """
    try:
        bucket = storage_client.bucket(GCS_BUCKET)
        blob_name = f"change_reports/{datetime.utcnow().strftime('%Y/%m/%d')}/{report['report_id']}.json"
        blob = bucket.blob(blob_name)

        blob.upload_from_string(json.dumps(report, indent=2), content_type="application/json")

        logger.info(f"Stored change report in GCS: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to store report in GCS: {e}")
        return False


@functions_framework.cloud_event
def change_report_handler(cloud_event: CloudEvent) -> None:
    """
    Main Cloud Function handler for Firestore change events.

    Args:
        cloud_event: CloudEvent from Firestore trigger
    """
    try:
        logger.info(f"Processing Firestore change event: {cloud_event.get('type', 'unknown')}")

        # Initialize clients
        firestore_client, storage_client = initialize_clients()

        # Extract change information
        change_info = extract_change_info(cloud_event)

        if "error" in change_info:
            logger.error(f"Failed to extract change info: {change_info['error']}")
            return

        # Skip reporting for change_reports collection to avoid infinite loops
        if change_info["collection"] == REPORTS_COLLECTION:
            logger.debug("Skipping change report for change_reports collection")
            return

        # Generate change report
        report = generate_change_report(change_info)

        # Store report based on configuration
        success = False

        if REPORT_STORAGE_MODE in ["firestore", "both"]:
            success = store_report_firestore(report, firestore_client) or success

        if REPORT_STORAGE_MODE in ["gcs", "both"]:
            success = store_report_gcs(report, storage_client) or success

        if success:
            logger.info(f"Successfully processed change report: {report['report_id']}")
        else:
            logger.error(f"Failed to store change report: {report['report_id']}")

    except Exception as e:
        logger.error(f"Error in change_report_handler: {e}", exc_info=True)


# For local testing
if __name__ == "__main__":
    # Create a mock CloudEvent for testing
    mock_event = CloudEvent(
        {
            "type": "google.cloud.firestore.document.v1.updated",
            "source": "//firestore.googleapis.com/projects/chatgpt-db-project/databases/(default)",
            "data": {
                "value": {
                    "name": "projects/chatgpt-db-project/databases/(default)/documents/document_metadata/test_doc_123",
                    "fields": {
                        "vectorStatus": {"stringValue": "completed"},
                        "version": {"integerValue": "2"},
                        "lastUpdated": {"timestampValue": "2025-01-27T19:00:00Z"},
                    },
                },
                "oldValue": {
                    "fields": {
                        "vectorStatus": {"stringValue": "pending"},
                        "version": {"integerValue": "1"},
                        "lastUpdated": {"timestampValue": "2025-01-27T18:00:00Z"},
                    }
                },
            },
        }
    )

    print("Testing change report function...")
    change_report_handler(mock_event)
