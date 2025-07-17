"""
Cloud Function: MCP Handler
Main handler for Agent-to-Agent Communication via API Gateway
Handles document operations, vector search, and RAG queries
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
from ADK.agent_data.tools.qdrant_vectorization_tool import (
    QdrantVectorizationTool,
    qdrant_rag_search,
)
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
vectorization_tool = None
auth_manager = None
monitoring_client = None
workflows_client = None


def _initialize_components():
    """Initialize all required components for the Cloud Function."""
    global qdrant_store, firestore_manager, vectorization_tool, auth_manager
    global monitoring_client, workflows_client

    try:
        # Initialize vector store and tools
        qdrant_store = QdrantStore()
        firestore_manager = FirestoreMetadataManager()
        vectorization_tool = QdrantVectorizationTool()
        auth_manager = AuthManager()

        # Initialize monitoring and workflows clients
        monitoring_client = monitoring_v3.MetricServiceClient()
        workflows_client = workflows_v1.WorkflowsClient()

        logger.info("All components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
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

        # Create metric descriptor if needed
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/mcp_gateway/{operation}_latency"
        series.resource.type = "cloud_function"
        series.resource.labels["function_name"] = "mcp-handler"

        # Add data point
        point = monitoring_v3.Point()
        point.value.double_value = latency_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        monitoring_client.create_time_series(name=project_name, time_series=[series])

    except Exception as e:
        logger.warning(f"Failed to record metric: {e}")


def _trigger_workflow(workflow_name: str, data: dict[str, Any]) -> str | None:
    """Trigger a Cloud Workflow for complex operations."""
    try:
        if not workflows_client:
            return None

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")

        parent = f"projects/{project_id}/locations/{location}/workflows/{workflow_name}"

        execution = {"argument": json.dumps(data)}

        response = workflows_client.create_execution(parent=parent, execution=execution)

        logger.info(f"Triggered workflow {workflow_name}: {response.name}")
        return response.name

    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
        return None


@functions_framework.http
def mcp_handler(request: Request):
    """
    Main Cloud Function handler for MCP Gateway operations.
    Routes requests to appropriate handlers based on path and method.
    """
    start_time = time.time()

    # Initialize components on first request
    if qdrant_store is None:
        _initialize_components()

    try:
        # Parse request
        path = request.path.strip("/")
        method = request.method

        logger.info(f"Processing {method} /{path}")

        # Health check endpoint
        if path == "health":
            return _handle_health_check()

        # Authentication endpoints (delegate to auth handler)
        if path.startswith("auth/"):
            return _handle_auth_request(request, path)

        # Validate authentication for protected endpoints
        user_info = _validate_auth_token(request)
        if not user_info:
            return jsonify({"error": "Unauthorized"}), 401

        # Route to appropriate handler
        if path == "save" and method == "POST":
            result = _handle_save_document(request, user_info)
        elif path == "query" and method == "POST":
            result = _handle_query_vectors(request, user_info)
        elif path == "search" and method == "POST":
            result = _handle_search_documents(request, user_info)
        elif path == "rag" and method == "POST":
            result = _handle_rag_search(request, user_info)
        else:
            return jsonify({"error": "Endpoint not found"}), 404

        # Record latency
        latency_ms = (time.time() - start_time) * 1000
        _record_latency_metric(path, latency_ms)

        return result

    except Exception as e:
        logger.error(f"Handler error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _handle_health_check():
    """Handle health check requests."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0-cf",
            "services": {
                "qdrant": "connected" if qdrant_store else "disconnected",
                "firestore": "connected" if firestore_manager else "disconnected",
            },
        }
    )


def _handle_auth_request(request: Request, path: str):
    """Handle authentication requests by delegating to auth Cloud Function."""
    # This will be handled by a separate auth_handler Cloud Function
    # For now, return a placeholder
    return jsonify({"error": "Auth endpoint moved to separate function"}), 302


def _handle_save_document(request: Request, user_info: dict[str, Any]):
    """Handle document saving with vector embedding."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        doc_id = data.get("doc_id")
        content = data.get("content")
        metadata = data.get("metadata", {})
        tag = data.get("tag")
        update_firestore = data.get("update_firestore", True)

        if not doc_id or not content:
            return jsonify({"error": "doc_id and content are required"}), 400

        # Add user context to metadata
        metadata["user_id"] = user_info["user_id"]
        metadata["created_at"] = time.time()

        # For complex operations, trigger workflow
        if len(content) > 10000 or metadata.get("complex_processing"):
            workflow_data = {
                "operation": "save_document",
                "doc_id": doc_id,
                "content": content,
                "metadata": metadata,
                "tag": tag,
                "update_firestore": update_firestore,
                "user_info": user_info,
            }

            execution_name = _trigger_workflow("mcp-document-processing", workflow_data)

            return jsonify(
                {
                    "status": "processing",
                    "doc_id": doc_id,
                    "message": "Document queued for processing",
                    "workflow_execution": execution_name,
                }
            )

        # Handle simple operations directly
        vector_result = vectorization_tool.vectorize_and_store(
            doc_id=doc_id, content=content, metadata=metadata, tag=tag
        )

        firestore_updated = False
        if update_firestore and vector_result.get("success"):
            try:
                firestore_manager.save_document_metadata(
                    doc_id=doc_id,
                    metadata=metadata,
                    vector_id=vector_result.get("vector_id"),
                )
                firestore_updated = True
            except Exception as e:
                logger.warning(f"Firestore update failed: {e}")

        return jsonify(
            {
                "status": "success",
                "doc_id": doc_id,
                "message": "Document saved successfully",
                "vector_id": vector_result.get("vector_id"),
                "embedding_dimension": vector_result.get("embedding_dimension"),
                "firestore_updated": firestore_updated,
            }
        )

    except Exception as e:
        logger.error(f"Save document error: {e}")
        return jsonify({"error": str(e)}), 500


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

        # Perform vector search
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

        # Search documents
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
            }
        )

    except Exception as e:
        logger.error(f"Search documents error: {e}")
        return jsonify({"error": str(e)}), 500


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

        # For complex RAG operations, trigger workflow
        if len(query_text) > 1000 or metadata_filters.get("complex_rag"):
            workflow_data = {
                "operation": "rag_search",
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
                    "message": "RAG search queued for processing",
                    "workflow_execution": execution_name,
                }
            )

        # Handle simple RAG operations directly
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
            }
        )

    except Exception as e:
        logger.error(f"RAG search error: {e}")
        return jsonify({"error": str(e)}), 500
