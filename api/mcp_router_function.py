"""
Cloud Function: MCP Router
Lightweight routing gateway for Agent-to-Agent Communication
Routes requests to specialized Cloud Functions based on operation type
Optimized for 80% Cloud Functions, 15% Workflows, <5% Cloud Run architecture
"""

import logging
import os
import time

import functions_framework
import requests
from flask import Request, jsonify
from google.cloud import monitoring_v3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function URLs (environment variables)
DOCUMENT_INGESTION_URL = os.getenv("DOCUMENT_INGESTION_URL")
VECTOR_SEARCH_URL = os.getenv("VECTOR_SEARCH_URL")
RAG_SEARCH_URL = os.getenv("RAG_SEARCH_URL")
AUTH_HANDLER_URL = os.getenv("AUTH_HANDLER_URL")

# Shadow traffic configuration (1%)
SHADOW_TRAFFIC_ENABLED = os.getenv("SHADOW_TRAFFIC_ENABLED", "true").lower() == "true"
SHADOW_TRAFFIC_PERCENTAGE = float(os.getenv("SHADOW_TRAFFIC_PERCENTAGE", "1.0"))

# Initialize monitoring
monitoring_client = None


def _initialize_components():
    """Initialize monitoring components."""
    global monitoring_client

    try:
        monitoring_client = monitoring_v3.MetricServiceClient()
        logger.info("MCP router components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize router components: {e}")
        raise


def _record_routing_metric(operation: str, target_function: str, latency_ms: float):
    """Record routing metrics to Cloud Monitoring."""
    try:
        if not monitoring_client:
            return

        project_name = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}"

        # Create metric for routing decisions
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/mcp_router/routing_latency"
        series.resource.type = "cloud_function"
        series.resource.labels["function_name"] = "mcp-router"
        series.metric.labels["operation"] = operation
        series.metric.labels["target_function"] = target_function

        # Add data point
        point = monitoring_v3.Point()
        point.value.double_value = latency_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        monitoring_client.create_time_series(name=project_name, time_series=[series])

    except Exception as e:
        logger.warning(f"Failed to record routing metric: {e}")


def _should_apply_shadow_traffic() -> bool:
    """Determine if request should receive shadow traffic."""
    if not SHADOW_TRAFFIC_ENABLED:
        return False

    import random

    return random.random() < (SHADOW_TRAFFIC_PERCENTAGE / 100.0)


def _route_request(target_url: str, request: Request, operation: str) -> tuple:
    """Route request to target Cloud Function."""
    try:
        start_time = time.time()

        # Prepare request data
        headers = {
            "Content-Type": "application/json",
            "Authorization": request.headers.get("Authorization", ""),
            "X-Routed-From": "mcp-router",
            "X-Operation-Type": operation,
        }

        # Forward the request
        if request.method == "GET":
            response = requests.get(
                f"{target_url}{request.path}",
                headers=headers,
                params=request.args,
                timeout=30,
            )
        else:
            response = requests.post(
                f"{target_url}{request.path}",
                headers=headers,
                json=request.get_json() if request.is_json else None,
                timeout=30,
            )

        # Record routing latency
        routing_latency = (time.time() - start_time) * 1000
        target_function = target_url.split("/")[-1] if target_url else "unknown"
        _record_routing_metric(operation, target_function, routing_latency)

        return response.json(), response.status_code

    except requests.exceptions.Timeout:
        logger.error(f"Timeout routing to {target_url}")
        return {"error": "Request timeout"}, 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Routing error to {target_url}: {e}")
        return {"error": "Service unavailable"}, 503
    except Exception as e:
        logger.error(f"Unexpected routing error: {e}")
        return {"error": "Internal routing error"}, 500


def _determine_target_function(path: str, method: str) -> tuple:
    """Determine which specialized function should handle the request."""

    # Document ingestion operations (30% of traffic)
    if path in ["save", "batch_save"] and method == "POST":
        return DOCUMENT_INGESTION_URL, "document_ingestion"

    # Vector search operations (40% of traffic)
    elif path in ["query", "search", "batch_query"] and method == "POST":
        return VECTOR_SEARCH_URL, "vector_search"

    # RAG search operations (25% of traffic)
    elif path in ["rag", "context_search", "batch_rag"] and method == "POST":
        return RAG_SEARCH_URL, "rag_search"

    # Authentication operations (5% of traffic)
    elif path.startswith("auth/"):
        return AUTH_HANDLER_URL, "authentication"

    # Health checks can be handled by any function
    elif path == "health":
        return DOCUMENT_INGESTION_URL, "health_check"  # Default to document ingestion

    else:
        return None, "unknown"


@functions_framework.http
def mcp_router(request: Request):
    """
    Lightweight MCP Router for Agent-to-Agent Communication.
    Routes requests to specialized Cloud Functions based on operation type.
    """
    start_time = time.time()

    # Initialize components on first request
    if monitoring_client is None:
        _initialize_components()

    try:
        # Parse request
        path = request.path.strip("/")
        method = request.method

        logger.info(f"Routing {method} /{path}")

        # Determine target function
        target_url, operation = _determine_target_function(path, method)

        if not target_url:
            return (
                jsonify(
                    {
                        "error": "Operation not supported",
                        "path": path,
                        "method": method,
                        "router": "mcp-router",
                    }
                ),
                404,
            )

        # Route the request
        result, status_code = _route_request(target_url, request, operation)

        # Add routing metadata
        if isinstance(result, dict):
            result["routing_info"] = {
                "router": "mcp-router",
                "target_function": operation,
                "routing_latency_ms": (time.time() - start_time) * 1000,
                "shadow_traffic": _should_apply_shadow_traffic(),
            }

        # Apply shadow traffic if enabled (1% of requests)
        if _should_apply_shadow_traffic() and operation != "health_check":
            try:
                # Send shadow request (don't wait for response)
                import threading

                shadow_thread = threading.Thread(
                    target=_route_request,
                    args=(target_url, request, f"shadow_{operation}"),
                )
                shadow_thread.daemon = True
                shadow_thread.start()

                if isinstance(result, dict):
                    result["routing_info"]["shadow_sent"] = True

            except Exception as e:
                logger.warning(f"Shadow traffic failed: {e}")

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Router error: {e}")
        return (
            jsonify(
                {
                    "error": "Router internal error",
                    "message": str(e),
                    "router": "mcp-router",
                }
            ),
            500,
        )


def _handle_health_check():
    """Handle health check for the router itself."""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.0.0-router",
            "architecture": "80%CF-15%WF-5%CR",
            "functions": {
                "document_ingestion": (
                    "configured" if DOCUMENT_INGESTION_URL else "not configured"
                ),
                "vector_search": (
                    "configured" if VECTOR_SEARCH_URL else "not configured"
                ),
                "rag_search": "configured" if RAG_SEARCH_URL else "not configured",
                "auth_handler": "configured" if AUTH_HANDLER_URL else "not configured",
            },
            "shadow_traffic": {
                "enabled": SHADOW_TRAFFIC_ENABLED,
                "percentage": SHADOW_TRAFFIC_PERCENTAGE,
            },
        }
    )
