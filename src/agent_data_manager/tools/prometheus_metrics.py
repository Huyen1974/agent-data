"""Prometheus metrics collection and Pushgateway integration for QdrantStore."""

import os
import logging
import threading
import time
import requests
from typing import Optional, Dict, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client.exposition import generate_latest

logger = logging.getLogger(__name__)

# Metrics registry for QdrantStore
qdrant_registry = CollectorRegistry()

# QdrantStore metrics
qdrant_requests_total = Counter(
    "qdrant_requests_total", "Total number of requests to Qdrant", ["operation", "status"], registry=qdrant_registry
)

qdrant_request_duration_seconds = Histogram(
    "qdrant_request_duration_seconds", "Request duration to Qdrant in seconds", ["operation"], registry=qdrant_registry
)

qdrant_vector_count = Gauge(
    "qdrant_vector_count", "Current number of vectors in Qdrant collection", ["collection"], registry=qdrant_registry
)

qdrant_api_errors_total = Counter(
    "qdrant_api_errors_total", "Total number of API errors with Qdrant", ["error_type"], registry=qdrant_registry
)

qdrant_connection_status = Gauge(
    "qdrant_connection_status", "Qdrant connection status (1=connected, 0=disconnected)", registry=qdrant_registry
)

# Business metrics
documents_processed_total = Counter(
    "documents_processed_total", "Total number of documents processed", registry=qdrant_registry
)

semantic_searches_total = Counter(
    "semantic_searches_total", "Total number of semantic searches performed", registry=qdrant_registry
)

embedding_generation_duration_seconds = Histogram(
    "embedding_generation_duration_seconds", "Duration of embedding generation in seconds", registry=qdrant_registry
)

# A2A API metrics
a2a_api_requests_total = Counter(
    "a2a_api_requests_total", "Total number of A2A API requests", ["endpoint", "status"], registry=qdrant_registry
)

a2a_api_request_duration_seconds = Histogram(
    "a2a_api_request_duration_seconds", "A2A API request duration in seconds", ["endpoint"], registry=qdrant_registry
)

a2a_api_errors_total = Counter(
    "a2a_api_errors_total", "Total number of A2A API errors", ["endpoint", "error_type"], registry=qdrant_registry
)

# RAG performance metrics
rag_search_duration_seconds = Histogram(
    "rag_search_duration_seconds", "RAG search duration in seconds", ["search_type"], registry=qdrant_registry
)

rag_cache_hits_total = Counter("rag_cache_hits_total", "Total number of RAG cache hits", registry=qdrant_registry)

rag_cache_misses_total = Counter("rag_cache_misses_total", "Total number of RAG cache misses", registry=qdrant_registry)

rag_results_count = Histogram(
    "rag_results_count", "Number of results returned by RAG searches", ["search_type"], registry=qdrant_registry
)

# CSKH Agent specific metrics
cskh_queries_total = Counter(
    "cskh_queries_total", "Total number of CSKH agent queries", ["status"], registry=qdrant_registry
)

cskh_query_duration_seconds = Histogram(
    "cskh_query_duration_seconds", "CSKH query duration in seconds", registry=qdrant_registry
)


def push_to_pushgateway(gateway_url: str, job: str, registry: CollectorRegistry, timeout: int = 10):
    """
    Push metrics to Prometheus Pushgateway using HTTP POST.

    Args:
        gateway_url: URL of the Pushgateway
        job: Job name for the metrics
        registry: Prometheus registry containing metrics
        timeout: Request timeout in seconds
    """
    # Generate metrics data
    metrics_data = generate_latest(registry)

    # Construct the URL for the specific job
    url = f"{gateway_url}/metrics/job/{job}"

    # Send POST request to Pushgateway
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    response = requests.post(url, data=metrics_data, headers=headers, timeout=timeout)
    response.raise_for_status()  # Raise exception for HTTP errors


class MetricsPusher:
    """Handles pushing metrics to Prometheus Pushgateway."""

    def __init__(self, pushgateway_url: Optional[str] = None, push_interval: int = 60):
        """
        Initialize the metrics pusher.

        Args:
            pushgateway_url: URL of the Prometheus Pushgateway
            push_interval: Interval in seconds between metric pushes
        """
        self.pushgateway_url = pushgateway_url or os.environ.get("PUSHGATEWAY_URL")
        self.push_interval = push_interval
        self._stop_event = threading.Event()
        self._push_thread: Optional[threading.Thread] = None
        self._running = False

        if self.pushgateway_url:
            logger.info(f"MetricsPusher initialized with URL: {self.pushgateway_url}")
        else:
            logger.warning("PUSHGATEWAY_URL not set, metrics will not be pushed")

    def start(self):
        """Start the background thread for pushing metrics."""
        if not self.pushgateway_url:
            logger.warning("Cannot start metrics pusher: PUSHGATEWAY_URL not configured")
            return

        if self._running:
            logger.warning("MetricsPusher is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._push_thread = threading.Thread(target=self._push_loop, daemon=True)
        self._push_thread.start()
        logger.info(f"MetricsPusher started with {self.push_interval}s interval")

    def stop(self):
        """Stop the background thread for pushing metrics."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._push_thread:
            self._push_thread.join(timeout=5)
            self._push_thread = None

        logger.info("MetricsPusher stopped")

    def _push_loop(self):
        """Background loop that pushes metrics at regular intervals."""
        while not self._stop_event.wait(self.push_interval):
            try:
                self.push_metrics()
            except Exception as e:
                logger.error(f"Error pushing metrics: {e}")

    def push_metrics(self):
        """Push metrics to the Pushgateway."""
        if not self.pushgateway_url:
            logger.debug("No pushgateway URL configured, skipping metrics push")
            return

        try:
            push_to_pushgateway(
                gateway_url=self.pushgateway_url, job="qdrant-store", registry=qdrant_registry, timeout=10
            )
            logger.debug("Successfully pushed metrics to Pushgateway")
        except Exception as e:
            logger.error(f"Failed to push metrics to Pushgateway: {e}")


# Global metrics pusher instance
_metrics_pusher: Optional[MetricsPusher] = None


def initialize_metrics_pusher(pushgateway_url: Optional[str] = None, push_interval: int = 60):
    """
    Initialize and start the global metrics pusher.

    Args:
        pushgateway_url: URL of the Prometheus Pushgateway
        push_interval: Interval in seconds between metric pushes
    """
    global _metrics_pusher

    if _metrics_pusher:
        _metrics_pusher.stop()

    _metrics_pusher = MetricsPusher(pushgateway_url, push_interval)
    _metrics_pusher.start()


def shutdown_metrics_pusher():
    """Shutdown the global metrics pusher."""
    global _metrics_pusher

    if _metrics_pusher:
        _metrics_pusher.stop()
        _metrics_pusher = None


def record_qdrant_request(operation: str, status: str, duration: float):
    """
    Record a Qdrant request with metrics.

    Args:
        operation: The operation performed (e.g., 'search', 'upsert', 'delete')
        status: Status of the request ('success', 'error')
        duration: Duration of the request in seconds
    """
    qdrant_requests_total.labels(operation=operation, status=status).inc()
    qdrant_request_duration_seconds.labels(operation=operation).observe(duration)


def record_qdrant_error(error_type: str):
    """
    Record a Qdrant API error.

    Args:
        error_type: Type of error (e.g., 'connection', 'timeout', 'api')
    """
    qdrant_api_errors_total.labels(error_type=error_type).inc()


def update_qdrant_connection_status(connected: bool):
    """
    Update the Qdrant connection status.

    Args:
        connected: True if connected, False if disconnected
    """
    qdrant_connection_status.set(1 if connected else 0)


def update_vector_count(collection: str, count: int):
    """
    Update the vector count for a collection.

    Args:
        collection: Name of the collection
        count: Current number of vectors
    """
    qdrant_vector_count.labels(collection=collection).set(count)


def record_document_processed():
    """Record that a document was processed."""
    documents_processed_total.inc()


def record_semantic_search():
    """Record that a semantic search was performed."""
    semantic_searches_total.inc()


def record_embedding_generation(duration: float):
    """
    Record embedding generation duration.

    Args:
        duration: Duration in seconds
    """
    embedding_generation_duration_seconds.observe(duration)


def record_a2a_api_request(endpoint: str, status: str, duration: float):
    """
    Record A2A API request metrics.

    Args:
        endpoint: API endpoint name
        status: Request status ('success', 'error')
        duration: Request duration in seconds
    """
    a2a_api_requests_total.labels(endpoint=endpoint, status=status).inc()
    a2a_api_request_duration_seconds.labels(endpoint=endpoint).observe(duration)


def record_a2a_api_error(endpoint: str, error_type: str):
    """
    Record A2A API error.

    Args:
        endpoint: API endpoint name
        error_type: Type of error (e.g., 'timeout', 'validation', 'server')
    """
    a2a_api_errors_total.labels(endpoint=endpoint, error_type=error_type).inc()


def record_rag_search(search_type: str, duration: float, result_count: int, cached: bool = False):
    """
    Record RAG search metrics.

    Args:
        search_type: Type of RAG search ('standard', 'cskh', 'hybrid')
        duration: Search duration in seconds
        result_count: Number of results returned
        cached: Whether result was served from cache
    """
    rag_search_duration_seconds.labels(search_type=search_type).observe(duration)
    rag_results_count.labels(search_type=search_type).observe(result_count)

    if cached:
        rag_cache_hits_total.inc()
    else:
        rag_cache_misses_total.inc()


def record_cskh_query(status: str, duration: float):
    """
    Record CSKH agent query metrics.

    Args:
        status: Query status ('success', 'error', 'timeout')
        duration: Query duration in seconds
    """
    cskh_queries_total.labels(status=status).inc()
    cskh_query_duration_seconds.observe(duration)


# Context manager for timing operations
class MetricsTimer:
    """Context manager for timing operations and recording metrics."""

    def __init__(self, operation: str):
        """
        Initialize the timer.

        Args:
            operation: Name of the operation being timed
        """
        self.operation = operation
        self.start_time = None
        self.duration = None

    def __enter__(self):
        """Start the timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and record metrics."""
        if self.start_time is not None:
            self.duration = time.time() - self.start_time

            # Determine status based on exception
            status = "error" if exc_type is not None else "success"

            # Record the metrics
            record_qdrant_request(self.operation, status, self.duration)

            # Record error type if there was an exception
            if exc_type is not None:
                error_type = "api" if hasattr(exc_val, "status_code") else "unknown"
                record_qdrant_error(error_type)


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of current metrics.

    Returns:
        Dictionary containing current metric values
    """
    try:
        summary = {
            "pushgateway_url": _metrics_pusher.pushgateway_url if _metrics_pusher else None,
            "pusher_running": _metrics_pusher._running if _metrics_pusher else False,
            "registry_collectors": len(list(qdrant_registry._collector_to_names.keys())),
        }
        return summary
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return {"error": str(e)}
