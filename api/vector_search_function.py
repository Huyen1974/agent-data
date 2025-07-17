"""
Cloud Function: Vector Search Handler
Specialized handler for vector similarity search and document retrieval operations
Optimized for 80% Cloud Functions architecture
"""

import json
import logging
import os
import time
from typing import Any

import functions_framework
from flask import Request, jsonify
from google.cloud import monitoring_v3, workflows_v1

from ADK.agent_data.auth.auth_manager import AuthManager
from ADK.agent_data.vector_store.firestore_metadata_manager import (
    FirestoreMetadataManager,
)

# Import Agent Data components
from ADK.agent_data.vector_store.qdrant_store import QdrantStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
qdrant_store = None
firestore_manager = None
auth_manager = None
monitoring_client = None
workflows_client = None


def _initialize_components():
    """Initialize all required components for the Cloud Function."""
    global qdrant_store, firestore_manager, auth_manager
    global monitoring_client, workflows_client

    try:
        # Initialize vector store and tools
        qdrant_store = QdrantStore()
        firestore_manager = FirestoreMetadataManager()
        auth_manager = AuthManager()

        # Initialize monitoring and workflows clients
        monitoring_client = monitoring_v3.MetricServiceClient()
        workflows_client = workflows_v1.WorkflowsClient()

        logger.info("Vector search components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize vector search components: {e}")
        raise


def _validate_auth_token(request: Request) -> dict[str, Any] | None:
    """Validate JWT token and return user info."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]
        user_info = auth_manager.verify_token(token)
        return user_info

    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        return None


def _record_latency_metric(operation: str, latency_ms: float):
    """Record latency metrics to Cloud Monitoring."""
    try:
        if not monitoring_client:
            return

        project_name = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}"

        # Create metric descriptor
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/vector_search/{operation}_latency"
        series.resource.type = "cloud_function"
        series.resource.labels["function_name"] = "vector-search"

        # Add data point
        point = monitoring_v3.Point()
        point.value.double_value = latency_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        monitoring_client.create_time_series(name=project_name, time_series=[series])

    except Exception as e:
        logger.warning(f"Failed to record metric: {e}")


def _trigger_workflow(workflow_name: str, data: dict[str, Any]) -> str | None:
    """Trigger a Cloud Workflow for complex search operations."""
    try:
        if not workflows_client:
            return None

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

        parent = f"projects/{project_id}/locations/{location}/workflows/{workflow_name}"

        execution = {"argument": json.dumps(data)}

        response = workflows_client.create_execution(parent=parent, execution=execution)

        logger.info(f"Triggered search workflow {workflow_name}: {response.name}")
        return response.name

    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
        return None


@functions_framework.http
def vector_search_handler(request: Request):
    """
    Specialized Cloud Function handler for vector search operations.
    Handles vector similarity queries and document searches.
    """
    start_time = time.time()

    # Initialize components on first request
    if qdrant_store is None:
        _initialize_components()

    try:
        # Parse request
        path = request.path.strip("/")
        method = request.method

        logger.info(f"Processing vector search {method} /{path}")

        # Health check endpoint
        if path == "health":
            return _handle_health_check()

        # Validate authentication for protected endpoints
        user_info = _validate_auth_token(request)
        if not user_info:
            return jsonify({"error": "Unauthorized"}), 401

        # Route to appropriate handler
        if path == "query" and method == "POST":
            result = _handle_query_vectors(request, user_info)
        elif path == "search" and method == "POST":
            result = _handle_search_documents(request, user_info)
        elif path == "batch_query" and method == "POST":
            result = _handle_batch_query(request, user_info)
        else:
            return jsonify({"error": "Endpoint not found"}), 404

        # Record latency
        latency_ms = (time.time() - start_time) * 1000
        _record_latency_metric(path, latency_ms)

        return result

    except Exception as e:
        logger.error(f"Vector search handler error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _handle_health_check():
    """Handle health check requests."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0-cf-vector-search",
            "services": {
                "qdrant": "connected" if qdrant_store else "disconnected",
                "firestore": "connected" if firestore_manager else "disconnected",
            },
        }
    )


def _handle_query_vectors(request: Request, user_info: dict[str, Any]):
    """Handle vector similarity queries."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        query_text = data.get("query_text")
        tag = data.get("tag")
        limit = data.get("limit", 10)
        score_threshold = data.get("score_threshold", 0.7)

        if not query_text:
            return jsonify({"error": "query_text is required"}), 400

        # Add user context for filtering
        user_filter = {"user_id": user_info["user_id"]}

        # For complex queries, trigger workflow (15% workflows)
        if len(query_text) > 1000 or limit > 100:
            workflow_data = {
                "operation": "complex_vector_query",
                "query_text": query_text,
                "tag": tag,
                "limit": limit,
                "score_threshold": score_threshold,
                "user_filter": user_filter,
                "user_info": user_info,
            }

            execution_name = _trigger_workflow("mcp-vector-search", workflow_data)

            return jsonify(
                {
                    "status": "processing",
                    "query": query_text,
                    "message": "Complex vector query queued for processing",
                    "workflow_execution": execution_name,
                    "handler": "vector-search-cf",
                }
            )

        # Handle simple operations directly (80% cloud functions)
        results = qdrant_store.search_similar_vectors(
            query_text=query_text,
            limit=limit,
            score_threshold=score_threshold,
            tag=tag,
            metadata_filter=user_filter,
        )

        return jsonify(
            {
                "status": "success",
                "query_text": query_text,
                "results": results,
                "total_found": len(results),
                "message": f"Found {len(results)} similar documents",
                "handler": "vector-search-cf",
            }
        )

    except Exception as e:
        logger.error(f"Query vectors error: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_search_documents(request: Request, user_info: dict[str, Any]):
    """Handle document search with metadata filtering."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        tag = data.get("tag")
        offset = data.get("offset", 0)
        limit = data.get("limit", 10)
        include_vectors = data.get("include_vectors", False)

        # Add user context for filtering
        user_filter = {"user_id": user_info["user_id"]}

        # For large result sets, trigger workflow (15% workflows)
        if limit > 50 or include_vectors:
            workflow_data = {
                "operation": "large_document_search",
                "tag": tag,
                "offset": offset,
                "limit": limit,
                "include_vectors": include_vectors,
                "user_filter": user_filter,
                "user_info": user_info,
            }

            execution_name = _trigger_workflow("mcp-document-search", workflow_data)

            return jsonify(
                {
                    "status": "processing",
                    "message": "Large document search queued for processing",
                    "workflow_execution": execution_name,
                    "handler": "vector-search-cf",
                }
            )

        # Handle simple operations directly (80% cloud functions)
        results = firestore_manager.search_documents(
            tag=tag,
            offset=offset,
            limit=limit,
            include_vectors=include_vectors,
            metadata_filter=user_filter,
        )

        return jsonify(
            {
                "status": "success",
                "results": results,
                "total_found": len(results),
                "offset": offset,
                "limit": limit,
                "message": f"Found {len(results)} documents",
                "handler": "vector-search-cf",
            }
        )

    except Exception as e:
        logger.error(f"Search documents error: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_batch_query(request: Request, user_info: dict[str, Any]):
    """Handle batch vector queries."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        queries = data.get("queries", [])
        if not queries:
            return jsonify({"error": "queries array is required"}), 400

        # For batch operations, always use workflow (15% workflows)
        workflow_data = {
            "operation": "batch_vector_queries",
            "queries": queries,
            "user_info": user_info,
        }

        execution_name = _trigger_workflow("mcp-batch-search", workflow_data)

        return jsonify(
            {
                "status": "processing",
                "batch_size": len(queries),
                "message": f"Batch of {len(queries)} queries queued for processing",
                "workflow_execution": execution_name,
                "handler": "vector-search-cf",
            }
        )

    except Exception as e:
        logger.error(f"Batch query error: {e}")
        return jsonify({"error": str(e)}), 500
