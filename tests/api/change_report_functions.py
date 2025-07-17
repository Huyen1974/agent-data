"""
Standalone functions extracted from change_report_function for testing.
This module contains the core logic without Google Cloud dependencies.
"""

from datetime import datetime
from typing import Any


def calculate_string_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings using a simple character-based approach.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not str1 and not str2:
        return 0.0
    if not str1 or not str2:
        return 0.0
    if str1 == str2:
        return 1.0

    # Simple character overlap similarity
    set1 = set(str1.lower())
    set2 = set(str2.lower())
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0


def analyze_change_impact(
    old_data: dict[str, Any], new_data: dict[str, Any], changes: dict[str, Any]
) -> dict[str, Any]:
    """
    Analyze the impact of changes on the system.

    Args:
        old_data: Previous document data
        new_data: Current document data
        changes: Change analysis results

    Returns:
        Impact analysis results
    """
    impact = {
        "overall_impact": "low",
        "affected_systems": [],
        "workflow_impact": [],
        "data_consistency_risk": "low",
        "performance_impact": "minimal",
    }

    # Check for critical field changes
    critical_fields = ["vectorStatus", "doc_id", "original_text"]
    high_impact_fields = ["level_1", "version", "tags"]

    for change in changes.get("significant_changes", []):
        field = change.get("field", "")
        importance = change.get("importance", "low")

        if field in critical_fields or importance == "critical":
            impact["overall_impact"] = "critical"
            if field == "vectorStatus":
                impact["affected_systems"].extend(
                    ["vector_search", "embedding_pipeline"]
                )
                if new_data.get("vectorStatus") == "completed":
                    impact["workflow_impact"].append("vectorization_completed")
                elif new_data.get("vectorStatus") == "failed":
                    impact["workflow_impact"].append("vectorization_failed")
        elif field in high_impact_fields or importance == "high":
            if impact["overall_impact"] not in ["critical"]:
                impact["overall_impact"] = "high"
            impact["affected_systems"].append("metadata_search")

    # Assess data consistency risk
    if len(changes.get("modified_fields", [])) > 5:
        impact["data_consistency_risk"] = "high"
    elif len(changes.get("modified_fields", [])) > 2:
        impact["data_consistency_risk"] = "medium"

    return impact


def calculate_data_quality_metrics(
    old_data: dict[str, Any], new_data: dict[str, Any]
) -> dict[str, Any]:
    """
    Calculate data quality metrics for the change.

    Args:
        old_data: Previous document data
        new_data: Current document data

    Returns:
        Data quality metrics
    """
    metrics = {
        "completeness_score": 0.0,
        "consistency_score": 0.0,
        "validity_score": 0.0,
        "quality_trend": "stable",
    }

    # Required fields for completeness
    required_fields = ["doc_id", "vectorStatus", "level_1"]
    optional_fields = [
        "level_2",
        "level_3",
        "tags",
        "auto_tags",
        "lastUpdated",
        "original_text",
    ]

    # Calculate completeness score
    old_complete = sum(
        1 for field in required_fields + optional_fields if old_data.get(field)
    )
    new_complete = sum(
        1 for field in required_fields + optional_fields if new_data.get(field)
    )
    total_fields = len(required_fields + optional_fields)

    metrics["completeness_score"] = (
        new_complete / total_fields if total_fields > 0 else 0.0
    )

    # Calculate consistency score (hierarchy levels filled consistently)
    hierarchy_levels = ["level_1", "level_2", "level_3"]
    filled_levels = sum(1 for level in hierarchy_levels if new_data.get(level))
    metrics["consistency_score"] = filled_levels / len(hierarchy_levels)

    # Calculate validity score (required fields present)
    valid_required = sum(1 for field in required_fields if new_data.get(field))
    metrics["validity_score"] = valid_required / len(required_fields)

    # Determine quality trend
    if new_complete > old_complete:
        metrics["quality_trend"] = "improving"
    elif new_complete < old_complete:
        metrics["quality_trend"] = "declining"
    else:
        metrics["quality_trend"] = "stable"

    return metrics


def convert_firestore_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """
    Convert Firestore field format to simple Python values.

    Args:
        fields: Firestore fields dictionary

    Returns:
        Simple dictionary with converted values
    """
    simple_dict = {}

    for field_name, field_value in fields.items():
        if isinstance(field_value, dict):
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
                array_values = field_value["arrayValue"].get("values", [])
                simple_dict[field_name] = [
                    convert_firestore_fields({"temp": val})["temp"]
                    for val in array_values
                ]
            elif "mapValue" in field_value:
                simple_dict[field_name] = convert_firestore_fields(
                    field_value["mapValue"].get("fields", {})
                )
            else:
                simple_dict[field_name] = field_value
        else:
            simple_dict[field_name] = field_value

    return simple_dict


def analyze_changes(
    old_value: dict[str, Any], new_value: dict[str, Any]
) -> dict[str, Any]:
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
                    {
                        "field": field,
                        "value": new_simple[field],
                        "type": type(new_simple[field]).__name__,
                    }
                )

        # Find removed fields
        for field in old_simple:
            if field not in new_simple:
                changes["removed_fields"].append(
                    {
                        "field": field,
                        "old_value": old_simple[field],
                        "type": type(old_simple[field]).__name__,
                    }
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
                if isinstance(old_simple[field], str) and isinstance(
                    new_simple[field], str
                ):
                    change_detail["length_change"] = len(new_simple[field]) - len(
                        old_simple[field]
                    )
                    change_detail["similarity"] = calculate_string_similarity(
                        old_simple[field], new_simple[field]
                    )

                # Analyze numeric changes
                if isinstance(old_simple[field], (int, float)) and isinstance(
                    new_simple[field], (int, float)
                ):
                    change_detail["numeric_change"] = (
                        new_simple[field] - old_simple[field]
                    )
                    change_detail["percent_change"] = (
                        (
                            (new_simple[field] - old_simple[field])
                            / old_simple[field]
                            * 100
                        )
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
                    {
                        "field": field,
                        "importance": significant_fields[field],
                        "change_type": change["change_type"],
                    }
                )

        # Impact analysis
        changes["impact_analysis"] = analyze_change_impact(
            old_simple, new_simple, changes
        )

        # Data quality metrics
        changes["data_quality_metrics"] = calculate_data_quality_metrics(
            old_simple, new_simple
        )

        return changes

    except Exception as e:
        return {"error": str(e)}


def generate_change_report(change_info: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a comprehensive change report.

    Args:
        change_info: Change information from CloudEvent

    Returns:
        Formatted change report
    """
    report = {
        "report_id": f"change_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat(),
        "event_info": {
            "event_type": change_info.get("event_type", "unknown"),
            "operation_type": change_info.get("operation_type", "unknown"),
            "collection": change_info.get("collection", "unknown"),
            "document_id": change_info.get("document_id", "unknown"),
        },
        "changes": {},
        "impact_assessment": {},
        "recommendations": [],
        "metadata": {
            "report_version": "1.0",
            "generated_by": "change_report_function",
            "processing_time_ms": 0,
        },
    }

    # Analyze changes if we have old and new values
    old_value = change_info.get("old_value", {})
    new_value = change_info.get("new_value", {})

    if old_value or new_value:
        report["changes"] = analyze_changes(old_value, new_value)
        report["impact_assessment"] = report["changes"].get("impact_analysis", {})

        # Generate recommendations based on changes
        recommendations = []

        if report["impact_assessment"].get("overall_impact") == "critical":
            recommendations.append("Review critical changes immediately")
            recommendations.append("Verify system functionality after changes")

        if "vectorization_completed" in report["impact_assessment"].get(
            "workflow_impact", []
        ):
            recommendations.append("Update vector search indexes")
            recommendations.append("Verify embedding quality")

        if (
            report["changes"].get("data_quality_metrics", {}).get("quality_trend")
            == "declining"
        ):
            recommendations.append("Review data quality issues")
            recommendations.append("Consider data validation improvements")

        report["recommendations"] = recommendations

    return report
