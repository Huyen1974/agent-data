"""
Cloud Function: RAG Search Handler
Specialized handler for Retrieval-Augmented Generation search operations
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
from ADK.agent_data.tools.qdrant_vectorization_tool import qdrant_rag_search
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

        logger.info("RAG search components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize RAG search components: {e}")
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
        series.metric.type = f"custom.googleapis.com/rag_search/{operation}_latency"
        series.resource.type = "cloud_function"
        series.resource.labels["function_name"] = "rag-search"

        # Add data point
        point = monitoring_v3.Point()
        point.value.double_value = latency_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        monitoring_client.create_time_series(name=project_name, time_series=[series])

    except Exception as e:
        logger.warning(f"Failed to record metric: {e}")


def _trigger_workflow(workflow_name: str, data: dict[str, Any]) -> str | None:
    """Trigger a Cloud Workflow for complex RAG operations."""
    try:
        if not workflows_client:
            return None

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

        parent = f"projects/{project_id}/locations/{location}/workflows/{workflow_name}"

        execution = {"argument": json.dumps(data)}

        response = workflows_client.create_execution(parent=parent, execution=execution)

        logger.info(f"Triggered RAG workflow {workflow_name}: {response.name}")
        return response.name

    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
        return None


@functions_framework.http
def rag_search_handler(request: Request):
    """
    Specialized Cloud Function handler for RAG search operations.
    Handles retrieval-augmented generation queries and context building.
    """
    start_time = time.time()

    # Initialize components on first request
    if qdrant_store is None:
        _initialize_components()

    try:
        # Parse request
        path = request.path.strip("/")
        method = request.method

        logger.info(f"Processing RAG search {method} /{path}")

        # Health check endpoint
        if path == "health":
            return _handle_health_check()

        # Validate authentication for protected endpoints
        user_info = _validate_auth_token(request)
        if not user_info:
            return jsonify({"error": "Unauthorized"}), 401

        # Route to appropriate handler
        if path == "rag" and method == "POST":
            result = _handle_rag_search(request, user_info)
        elif path == "context_search" and method == "POST":
            result = _handle_context_search(request, user_info)
        elif path == "batch_rag" and method == "POST":
            result = _handle_batch_rag(request, user_info)
        else:
            return jsonify({"error": "Endpoint not found"}), 404

        # Record latency
        latency_ms = (time.time() - start_time) * 1000
        _record_latency_metric(path, latency_ms)

        return result

    except Exception as e:
        logger.error(f"RAG search handler error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _handle_health_check():
    """Handle health check requests."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0-cf-rag-search",
            "services": {
                "qdrant": "connected" if qdrant_store else "disconnected",
                "firestore": "connected" if firestore_manager else "disconnected",
            },
        }
    )


def _handle_rag_search(request: Request, user_info: dict[str, Any]):
    """Handle RAG (Retrieval-Augmented Generation) search."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        query_text = data.get("query_text")
        metadata_filters = data.get("metadata_filters", {})
        tags = data.get("tags")
        path_query = data.get("path_query")
        limit = data.get("limit", 10)
        score_threshold = data.get("score_threshold", 0.5)
        qdrant_tag = data.get("qdrant_tag")

        if not query_text:
            return jsonify({"error": "query_text is required"}), 400

        # Add user context to filters
        metadata_filters["user_id"] = user_info["user_id"]

        # For complex RAG operations, trigger workflow (15% workflows)
        if len(query_text) > 1000 or metadata_filters.get("complex_rag") or limit > 50:
            workflow_data = {
                "operation": "complex_rag_search",
                "query_text": query_text,
                "metadata_filters": metadata_filters,
                "tags": tags,
                "path_query": path_query,
                "limit": limit,
                "score_threshold": score_threshold,
                "qdrant_tag": qdrant_tag,
                "user_info": user_info,
            }

            execution_name = _trigger_workflow("mcp-rag-processing", workflow_data)

            return jsonify(
                {
                    "status": "processing",
                    "query": query_text,
                    "message": "Complex RAG search queued for processing",
                    "workflow_execution": execution_name,
                    "handler": "rag-search-cf",
                }
            )

        # Handle simple RAG operations directly (80% cloud functions)
        rag_results = qdrant_rag_search(
            query_text=query_text,
            metadata_filters=metadata_filters,
            tags=tags,
            path_query=path_query,
            limit=limit,
            score_threshold=score_threshold,
            qdrant_tag=qdrant_tag,
        )

        return jsonify(
            {
                "status": "success",
                "query": query_text,
                "results": rag_results.get("results", []),
                "count": len(rag_results.get("results", [])),
                "rag_info": rag_results.get("rag_info", {}),
                "message": f"RAG search completed with {len(rag_results.get('results', []))} results",
                "handler": "rag-search-cf",
            }
        )

    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_context_search(request: Request, user_info: dict[str, Any]):
    """Handle context building for RAG operations."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        query_text = data.get("query_text")
        context_size = data.get("context_size", 5)
        overlap_threshold = data.get("overlap_threshold", 0.8)

        if not query_text:
            return jsonify({"error": "query_text is required"}), 400

        # Add user context for filtering
        user_filter = {"user_id": user_info["user_id"]}

        # Build context using vector search
        context_results = qdrant_store.search_similar_vectors(
            query_text=query_text,
            limit=context_size * 2,  # Get more results to filter for context
            score_threshold=0.6,
            metadata_filter=user_filter,
        )

        # Filter and deduplicate context
        context_docs = []
        seen_content = set()

        for result in context_results[:context_size]:
            content_hash = hash(result.get("content", ""))
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                context_docs.append(
                    {
                        "content": result.get("content"),
                        "metadata": result.get("metadata", {}),
                        "score": result.get("score", 0.0),
                    }
                )

        return jsonify(
            {
                "status": "success",
                "query": query_text,
                "context_documents": context_docs,
                "context_size": len(context_docs),
                "message": f"Built context with {len(context_docs)} documents",
                "handler": "rag-search-cf",
            }
        )

    except Exception as e:
        logger.error(f"Context search error: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_batch_rag(request: Request, user_info: dict[str, Any]):
    """Handle batch RAG search operations."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        queries = data.get("queries", [])
        if not queries:
            return jsonify({"error": "queries array is required"}), 400

        # For batch operations, always use workflow (15% workflows)
        workflow_data = {
            "operation": "batch_rag_search",
            "queries": queries,
            "user_info": user_info,
        }

        execution_name = _trigger_workflow("mcp-batch-rag", workflow_data)

        return jsonify(
            {
                "status": "processing",
                "batch_size": len(queries),
                "message": f"Batch of {len(queries)} RAG queries queued for processing",
                "workflow_execution": execution_name,
                "handler": "rag-search-cf",
            }
        )

    except Exception as e:
        logger.error(f"Batch RAG error: {e}")
        return jsonify({"error": str(e)}), 500
