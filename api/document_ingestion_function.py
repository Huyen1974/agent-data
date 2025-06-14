"""
Cloud Function: Document Ingestion Handler
Specialized handler for document saving and vectorization operations
Optimized for 80% Cloud Functions architecture
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional

import functions_framework
from flask import Request, jsonify
from google.cloud import monitoring_v3
from google.cloud import workflows_v1

# Import Agent Data components
from ADK.agent_data.vector_store.qdrant_store import QdrantStore
from ADK.agent_data.vector_store.firestore_metadata_manager import FirestoreMetadataManager
from ADK.agent_data.tools.qdrant_vectorization_tool import QdrantVectorizationTool
from ADK.agent_data.config.settings import settings
from ADK.agent_data.auth.auth_manager import AuthManager

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
        
        logger.info("Document ingestion components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize document ingestion components: {e}")
        raise


def _validate_auth_token(request: Request) -> Optional[Dict[str, Any]]:
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
        series.metric.type = f"custom.googleapis.com/document_ingestion/{operation}_latency"
        series.resource.type = "cloud_function"
        series.resource.labels["function_name"] = "document-ingestion"
        
        # Add data point
        point = monitoring_v3.Point()
        point.value.double_value = latency_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]
        
        monitoring_client.create_time_series(
            name=project_name, 
            time_series=[series]
        )
        
    except Exception as e:
        logger.warning(f"Failed to record metric: {e}")


def _trigger_workflow(workflow_name: str, data: Dict[str, Any]) -> Optional[str]:
    """Trigger a Cloud Workflow for complex document processing."""
    try:
        if not workflows_client:
            return None
            
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        location = os.getenv('GOOGLE_CLOUD_REGION', 'us-central1')
        
        parent = f"projects/{project_id}/locations/{location}/workflows/{workflow_name}"
        
        execution = {
            "argument": json.dumps(data)
        }
        
        response = workflows_client.create_execution(
            parent=parent,
            execution=execution
        )
        
        logger.info(f"Triggered document processing workflow {workflow_name}: {response.name}")
        return response.name
        
    except Exception as e:
        logger.error(f"Failed to trigger workflow {workflow_name}: {e}")
        return None


@functions_framework.http
def document_ingestion_handler(request: Request):
    """
    Specialized Cloud Function handler for document ingestion operations.
    Handles document saving, vectorization, and metadata storage.
    """
    start_time = time.time()
    
    # Initialize components on first request
    if qdrant_store is None:
        _initialize_components()
    
    try:
        # Parse request
        path = request.path.strip('/')
        method = request.method
        
        logger.info(f"Processing document ingestion {method} /{path}")
        
        # Health check endpoint
        if path == "health":
            return _handle_health_check()
        
        # Validate authentication for protected endpoints
        user_info = _validate_auth_token(request)
        if not user_info:
            return jsonify({"error": "Unauthorized"}), 401
        
        # Route to appropriate handler
        if path == "save" and method == "POST":
            result = _handle_save_document(request, user_info)
        elif path == "batch_save" and method == "POST":
            result = _handle_batch_save(request, user_info)
        else:
            return jsonify({"error": "Endpoint not found"}), 404
        
        # Record latency
        latency_ms = (time.time() - start_time) * 1000
        _record_latency_metric(path, latency_ms)
        
        return result
        
    except Exception as e:
        logger.error(f"Document ingestion handler error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _handle_health_check():
    """Handle health check requests."""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0-cf-doc-ingestion",
        "services": {
            "qdrant": "connected" if qdrant_store else "disconnected",
            "firestore": "connected" if firestore_manager else "disconnected",
            "vectorization": "initialized" if vectorization_tool else "not initialized"
        }
    })


def _handle_save_document(request: Request, user_info: Dict[str, Any]):
    """Handle single document saving with vector embedding."""
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
        metadata["ingestion_function"] = "document-ingestion-cf"
        
        # For complex operations, trigger workflow (15% workflows)
        if len(content) > 10000 or metadata.get("complex_processing"):
            workflow_data = {
                "operation": "save_document",
                "doc_id": doc_id,
                "content": content,
                "metadata": metadata,
                "tag": tag,
                "update_firestore": update_firestore,
                "user_info": user_info
            }
            
            execution_name = _trigger_workflow("mcp-document-processing", workflow_data)
            
            return jsonify({
                "status": "processing",
                "doc_id": doc_id,
                "message": "Document queued for processing",
                "workflow_execution": execution_name,
                "handler": "document-ingestion-cf"
            })
        
        # Handle simple operations directly (80% cloud functions)
        vector_result = vectorization_tool.vectorize_and_store(
            doc_id=doc_id,
            content=content,
            metadata=metadata,
            tag=tag
        )
        
        firestore_updated = False
        if update_firestore and vector_result.get("success"):
            try:
                firestore_manager.save_document_metadata(
                    doc_id=doc_id,
                    metadata=metadata,
                    vector_id=vector_result.get("vector_id")
                )
                firestore_updated = True
            except Exception as e:
                logger.warning(f"Firestore update failed: {e}")
        
        return jsonify({
            "status": "success",
            "doc_id": doc_id,
            "message": "Document saved successfully",
            "vector_id": vector_result.get("vector_id"),
            "embedding_dimension": vector_result.get("embedding_dimension"),
            "firestore_updated": firestore_updated,
            "handler": "document-ingestion-cf"
        })
        
    except Exception as e:
        logger.error(f"Save document error: {e}")
        return jsonify({"error": str(e)}), 500


def _handle_batch_save(request: Request, user_info: Dict[str, Any]):
    """Handle batch document saving operations."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        documents = data.get("documents", [])
        if not documents:
            return jsonify({"error": "documents array is required"}), 400
        
        # For batch operations, always use workflow (15% workflows)
        workflow_data = {
            "operation": "batch_save_documents",
            "documents": documents,
            "user_info": user_info
        }
        
        execution_name = _trigger_workflow("mcp-document-batch-processing", workflow_data)
        
        return jsonify({
            "status": "processing",
            "batch_size": len(documents),
            "message": f"Batch of {len(documents)} documents queued for processing",
            "workflow_execution": execution_name,
            "handler": "document-ingestion-cf"
        })
        
    except Exception as e:
        logger.error(f"Batch save error: {e}")
        return jsonify({"error": str(e)}), 500 