"""
Enhanced Mock Manager for CLI140k Test Runtime Optimization
==========================================================

Centralized mock management system to reduce external dependencies
and improve test execution speed. Provides comprehensive mocking
for Qdrant, Firestore, OpenAI, and other external services.

Created for CLI140k test runtime optimization.
"""

import time
from contextlib import asynccontextmanager, contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class FastMockManager:
    """
    Fast mock manager optimized for test runtime performance.
    Provides pre-configured mocks with minimal overhead.
    """

    def __init__(self):
        self._qdrant_mock = None
        self._firestore_mock = None
        self._openai_mock = None
        self._setup_time = 0

    @contextmanager
    def fast_qdrant_mock(self, collection_name: str = "test_collection"):
        """
        Fast Qdrant mock with pre-configured responses.
        Optimized for <1s setup time.
        """
        start_time = time.time()

        mock_client = MagicMock()

        # Pre-configure common responses
        mock_client.collection_exists.return_value = True
        mock_client.create_collection.return_value = True
        mock_client.get_collection.return_value = MagicMock(
            vectors_count=100, status="green"
        )

        # Fast search response
        mock_client.search.return_value = [
            MagicMock(
                id=f"doc_{i}",
                score=0.9 - (i * 0.1),
                payload={"content": f"Test content {i}", "doc_id": f"doc_{i}"},
            )
            for i in range(5)
        ]

        # Fast upsert response
        mock_client.upsert.return_value = MagicMock(
            operation_id=12345, status="completed"
        )

        self._setup_time = time.time() - start_time

        with patch("qdrant_client.QdrantClient", return_value=mock_client):
            yield mock_client

    @contextmanager
    def fast_firestore_mock(self):
        """
        Fast Firestore mock with pre-configured responses.
        Optimized for minimal latency.
        """
        mock_client = AsyncMock()
        mock_collection = AsyncMock()
        mock_doc_ref = AsyncMock()
        mock_doc_snapshot = AsyncMock()

        # Configure document snapshot
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {
            "doc_id": "test_doc",
            "content": "test content",
            "version": 1,
            "lastUpdated": "2024-01-01T00:00:00Z",
        }

        # Configure document reference
        mock_doc_ref.get.return_value = mock_doc_snapshot
        mock_doc_ref.set.return_value = None
        mock_doc_ref.update.return_value = None

        # Configure collection
        mock_collection.document.return_value = mock_doc_ref
        mock_collection.add.return_value = (None, mock_doc_ref)

        # Configure client
        mock_client.collection.return_value = mock_collection

        with patch("google.cloud.firestore.AsyncClient", return_value=mock_client):
            yield {
                "client": mock_client,
                "collection": mock_collection,
                "doc_ref": mock_doc_ref,
                "doc_snapshot": mock_doc_snapshot,
            }

    @contextmanager
    def fast_openai_mock(self):
        """
        Fast OpenAI mock with pre-configured embeddings.
        Returns consistent embeddings for predictable tests.
        """
        mock_client = AsyncMock()

        # Pre-configured embedding response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536)  # Standard OpenAI embedding dimension
        ]
        mock_response.usage = MagicMock(prompt_tokens=10, total_tokens=10)

        mock_client.embeddings.create.return_value = mock_response

        with patch("openai.AsyncOpenAI", return_value=mock_client):
            yield mock_client

    @contextmanager
    def comprehensive_mock_suite(self):
        """
        Comprehensive mock suite for full test isolation.
        Combines all major service mocks for maximum speed.
        """
        with (
            self.fast_qdrant_mock() as qdrant_mock,
            self.fast_firestore_mock() as firestore_mock,
            self.fast_openai_mock() as openai_mock,
        ):

            yield {
                "qdrant": qdrant_mock,
                "firestore": firestore_mock,
                "openai": openai_mock,
                "setup_time": self._setup_time,
            }

    @asynccontextmanager
    async def async_mock_suite(self):
        """
        Async version of comprehensive mock suite.
        For async test functions requiring full isolation.
        """
        with self.comprehensive_mock_suite() as mocks:
            yield mocks


class NetworkMockManager:
    """
    Mock manager for network-dependent tests.
    Provides offline alternatives to external service calls.
    """

    @contextmanager
    def offline_mode(self):
        """
        Complete offline mode - all network calls are mocked.
        Prevents network timeouts and improves test reliability.
        """
        network_patches = [
            patch("httpx.AsyncClient"),
            patch("requests.get"),
            patch("requests.post"),
            patch("urllib.request.urlopen"),
        ]

        started_patches = []
        try:
            for p in network_patches:
                mock = p.start()
                mock.return_value = MagicMock(
                    status_code=200,
                    json=lambda: {"status": "success", "data": []},
                    text="Mock response",
                )
                started_patches.append(p)

            yield

        finally:
            for p in started_patches:
                p.stop()


# Global instances for easy access
fast_mock_manager = FastMockManager()
network_mock_manager = NetworkMockManager()


# Pytest fixtures for easy integration
@pytest.fixture
def fast_qdrant():
    """Fast Qdrant mock fixture."""
    with fast_mock_manager.fast_qdrant_mock() as mock:
        yield mock


@pytest.fixture
def fast_firestore():
    """Fast Firestore mock fixture."""
    with fast_mock_manager.fast_firestore_mock() as mock:
        yield mock


@pytest.fixture
def fast_openai():
    """Fast OpenAI mock fixture."""
    with fast_mock_manager.fast_openai_mock() as mock:
        yield mock


@pytest.fixture
def comprehensive_mocks():
    """Comprehensive mock suite fixture."""
    with fast_mock_manager.comprehensive_mock_suite() as mocks:
        yield mocks


@pytest.fixture
def offline_mode():
    """Offline mode fixture for network isolation."""
    with network_mock_manager.offline_mode():
        yield


@pytest.fixture
async def async_mocks():
    """Async comprehensive mock suite fixture."""
    async with fast_mock_manager.async_mock_suite() as mocks:
        yield mocks


# Performance monitoring decorator
def monitor_test_performance(func):
    """
    Decorator to monitor test performance and detect slow tests.
    Helps identify tests that need optimization.
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        runtime = end_time - start_time
        if runtime > 5.0:  # Flag tests taking >5s
            print(f"⚠️  Slow test detected: {func.__name__} took {runtime:.2f}s")

        return result

    return wrapper


# Async version of performance monitor
def monitor_async_test_performance(func):
    """Async version of performance monitoring decorator."""

    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()

        runtime = end_time - start_time
        if runtime > 5.0:
            print(f"⚠️  Slow async test detected: {func.__name__} took {runtime:.2f}s")

        return result

    return wrapper
