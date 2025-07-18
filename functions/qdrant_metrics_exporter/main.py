"""Cloud Function for exporting Qdrant metrics to Cloud Monitoring."""

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import functions_framework
import requests
from google.cloud import firestore, monitoring_v3, secretmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project configuration
PROJECT_ID = "chatgpt-db-project"
SECRET_NAME = "qdrant-api-key-sg"
REGION = "asia-southeast1"

# Qdrant configuration
QDRANT_URL = (
    "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io"
)
COLLECTION_NAME = "agent_data_vectors"

# Metrics configuration
PUSHGATEWAY_URL = os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091")
JOB_NAME = "qdrant-metrics-exporter"

# Initialize Firestore client for additional metrics
firestore_client = firestore.Client(project=PROJECT_ID)


def get_qdrant_api_key() -> str:
    """Retrieve Qdrant API key from Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to retrieve Qdrant API key: {e}")
        raise


def collect_firestore_metrics() -> dict[str, Any]:
    """Collect additional metrics from Firestore."""
    try:
        # Count documents processed in the last hour
        one_hour_ago = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

        # Query documents collection for recent activity
        docs_ref = firestore_client.collection("documents")
        recent_docs = docs_ref.where("last_updated", ">=", one_hour_ago).stream()

        documents_processed = 0
        semantic_searches = 0

        for doc in recent_docs:
            doc_data = doc.to_dict()
            if doc_data.get("vectorStatus") == "completed":
                documents_processed += 1

            # Count search operations from metadata
            if doc_data.get("search_count", 0) > 0:
                semantic_searches += doc_data.get("search_count", 0)

        # Get total document count
        total_docs = len(list(docs_ref.stream()))

        return {
            "documents_processed_total": documents_processed,
            "semantic_searches_total": semantic_searches,
            "total_documents": total_docs,
            "firestore_connection_status": 1,
        }

    except Exception as e:
        logger.error(f"Failed to collect Firestore metrics: {e}")
        return {
            "documents_processed_total": 0,
            "semantic_searches_total": 0,
            "total_documents": 0,
            "firestore_connection_status": 0,
            "firestore_error": str(e),
        }


def collect_qdrant_metrics(api_key: str) -> dict[str, Any]:
    """Collect metrics from Qdrant cluster."""
    headers = {"api-key": api_key}
    metrics = {}

    try:
        start_time = datetime.now(UTC)

        # Get cluster info (for connection validation)
        cluster_url = f"{QDRANT_URL}/cluster"
        response = requests.get(cluster_url, headers=headers, timeout=10)
        response.raise_for_status()

        # Get collection info
        collection_url = f"{QDRANT_URL}/collections/{COLLECTION_NAME}"
        response = requests.get(collection_url, headers=headers, timeout=10)
        response.raise_for_status()
        collection_info = response.json()

        # Calculate request latency
        end_time = datetime.now(UTC)
        request_duration = (end_time - start_time).total_seconds()

        # Extract metrics
        result = collection_info.get("result", {})
        metrics = {
            "qdrant_requests_total": 1,  # Increment for this request
            "qdrant_vector_count": result.get("vectors_count", 0),
            "qdrant_segments_count": result.get("segments_count", 0),
            "qdrant_disk_data_size": result.get("disk_data_size", 0),
            "qdrant_ram_data_size": result.get("ram_data_size", 0),
            "qdrant_connection_status": 1,  # Connected
            "collection_status": 1 if result.get("status") == "green" else 0,
            "qdrant_request_duration_seconds": request_duration,
            "embedding_generation_duration_seconds": request_duration
            * 0.7,  # Estimated embedding time
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info(f"Collected Qdrant metrics: {metrics}")
        return metrics

    except Exception as e:
        logger.error(f"Failed to collect Qdrant metrics: {e}")
        # Return error metrics
        return {
            "qdrant_requests_total": 1,
            "qdrant_connection_status": 0,  # Disconnected
            "qdrant_api_errors_total": 1,
            "qdrant_request_duration_seconds": 10.0,  # Timeout duration
            "embedding_generation_duration_seconds": 0.0,
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
        }


def push_metrics_to_pushgateway(metrics: dict[str, Any]) -> bool:
    """Push metrics to Prometheus Pushgateway."""
    try:
        # Convert metrics to Prometheus format
        prometheus_metrics = []

        for metric_name, value in metrics.items():
            if metric_name in ["timestamp", "error"]:
                continue

            if isinstance(value, (int, float)):
                prometheus_metrics.append(f"{metric_name} {value}")

        # Add timestamp
        prometheus_metrics.append(
            "# HELP qdrant_metrics_timestamp Unix timestamp of metrics collection"
        )
        prometheus_metrics.append("# TYPE qdrant_metrics_timestamp gauge")
        prometheus_metrics.append(
            f"qdrant_metrics_timestamp {datetime.now(UTC).timestamp()}"
        )

        metrics_data = "\n".join(prometheus_metrics) + "\n"

        # Push to Pushgateway
        url = f"{PUSHGATEWAY_URL}/metrics/job/{JOB_NAME}"
        headers = {"Content-Type": "text/plain; charset=utf-8"}

        response = requests.post(url, data=metrics_data, headers=headers, timeout=10)
        response.raise_for_status()

        logger.info(f"Successfully pushed metrics to Pushgateway: {url}")
        return True

    except Exception as e:
        logger.error(f"Failed to push metrics to Pushgateway: {e}")
        return False


def send_to_cloud_monitoring(metrics: dict[str, Any]) -> bool:
    """Send metrics directly to Cloud Monitoring."""
    try:
        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{PROJECT_ID}"

        series = []
        now = datetime.now(UTC)

        for metric_name, value in metrics.items():
            if metric_name in ["timestamp", "error"] or not isinstance(
                value, (int, float)
            ):
                continue

            # Create time series
            series.append(
                monitoring_v3.TimeSeries(
                    {
                        "metric": {
                            "type": f"custom.googleapis.com/qdrant/{metric_name}",
                            "labels": {
                                "collection": COLLECTION_NAME,
                                "region": REGION,
                                "source": "qdrant-metrics-exporter",
                            },
                        },
                        "resource": {
                            "type": "global",
                            "labels": {"project_id": PROJECT_ID},
                        },
                        "points": [
                            {
                                "interval": {
                                    "end_time": {"seconds": int(now.timestamp())}
                                },
                                "value": {"double_value": float(value)},
                            }
                        ],
                    }
                )
            )

        if series:
            client.create_time_series(name=project_name, time_series=series)
            logger.info(f"Successfully sent {len(series)} metrics to Cloud Monitoring")
            return True
        else:
            logger.warning("No valid metrics to send to Cloud Monitoring")
            return False

    except Exception as e:
        logger.error(f"Failed to send metrics to Cloud Monitoring: {e}")
        return False


@functions_framework.http
def export_qdrant_metrics(request):
    """HTTP Cloud Function to export Qdrant metrics."""
    try:
        # Get Qdrant API key
        api_key = get_qdrant_api_key()

        # Collect metrics from Qdrant
        qdrant_metrics = collect_qdrant_metrics(api_key)

        # Collect metrics from Firestore
        firestore_metrics = collect_firestore_metrics()

        # Combine all metrics
        metrics = {**qdrant_metrics, **firestore_metrics}

        # Push to Pushgateway (primary method)
        pushgateway_success = push_metrics_to_pushgateway(metrics)

        # Send to Cloud Monitoring (backup method)
        monitoring_success = send_to_cloud_monitoring(metrics)

        # Prepare response
        response = {
            "status": "success",
            "timestamp": metrics.get("timestamp"),
            "metrics_collected": len(
                [
                    k
                    for k, v in metrics.items()
                    if k not in ["timestamp", "error"] and isinstance(v, (int, float))
                ]
            ),
            "pushgateway_success": pushgateway_success,
            "cloud_monitoring_success": monitoring_success,
            "metrics": metrics,
        }

        if "error" in metrics:
            response["collection_error"] = metrics["error"]

        # Return success if at least one method worked
        if pushgateway_success or monitoring_success:
            logger.info("Metrics export completed successfully")
            return json.dumps(response), 200
        else:
            logger.error("Both Pushgateway and Cloud Monitoring failed")
            response["status"] = "partial_failure"
            return json.dumps(response), 500

    except Exception as e:
        logger.error(f"Metrics export failed: {e}")
        error_response = {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return json.dumps(error_response), 500


@functions_framework.cloud_event
def export_qdrant_metrics_scheduled(cloud_event):
    """Cloud Scheduler triggered function to export Qdrant metrics."""
    try:
        logger.info("Scheduled metrics export triggered")

        # Get Qdrant API key
        api_key = get_qdrant_api_key()

        # Collect and export metrics
        qdrant_metrics = collect_qdrant_metrics(api_key)
        firestore_metrics = collect_firestore_metrics()
        metrics = {**qdrant_metrics, **firestore_metrics}

        pushgateway_success = push_metrics_to_pushgateway(metrics)
        monitoring_success = send_to_cloud_monitoring(metrics)

        if pushgateway_success or monitoring_success:
            logger.info("Scheduled metrics export completed successfully")
        else:
            logger.error("Scheduled metrics export failed")

    except Exception as e:
        logger.error(f"Scheduled metrics export failed: {e}")
        raise
