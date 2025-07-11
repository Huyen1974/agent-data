@pytest.mark.integration
"""
Test suite for CLI140: CSKH Agent API and RAG performance optimization.

Tests the new /cskh_query endpoint with caching, metrics, and performance validation.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.agent_data_manager.api_mcp_gateway import app

# from src.agent_data_manager.tools.prometheus_metrics import (
#     cskh_queries_total,  # Unused import
#     rag_cache_hits_total,  # Unused import
#     rag_cache_misses_total,  # Unused import
# )



class TestCLI140CSKHRag:
    """Test suite for CLI140 CSKH Agent API and RAG optimization."""

    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_disabled(self):
        """Mock authentication disabled for testing."""
        with patch("src.agent_data_manager.config.settings.settings.ENABLE_AUTHENTICATION", False):
            yield

    @pytest.fixture
    def mock_qdrant_store(self):
        """Mock QdrantStore for testing."""
        mock_store = AsyncMock()
        mock_store.semantic_search.return_value = {
            "status": "success",
            "results": [
                {
                    "doc_id": "test_doc_1",
                    "content": "Customer care knowledge base content",
                    "score": 0.85,
                    "metadata": {"category": "billing", "priority": "high"},
                }
            ],
        }
        return mock_store

    @pytest.fixture
    def mock_rag_search(self):
        """Mock RAG search function."""

        async def mock_rag_search_func(*args, **kwargs):
            return {
                "status": "success",
                "query": kwargs.get("query_text", "test query"),
                "results": [
                    {
                        "doc_id": "cskh_doc_1",
                        "content": "CSKH knowledge base content for customer care",
                        "score": 0.9,
                        "metadata": {"department": "customer_service", "topic": "billing_inquiry"},
                    }
                ],
                "count": 1,
                "rag_info": {
                    "qdrant_results": 1,
                    "firestore_filtered": 1,
                    "metadata_filters": kwargs.get("metadata_filters", {}),
                    "score_threshold": kwargs.get("score_threshold", 0.6),
                },
            }

        return mock_rag_search_func

    @pytest.mark.asyncio
    async def test_cskh_query_endpoint_basic(self, client, mock_auth_disabled, mock_rag_search):
        """Test basic CSKH query endpoint functionality."""
        with patch("src.agent_data_manager.api_mcp_gateway.qdrant_rag_search", mock_rag_search), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store", AsyncMock()
        ), patch("src.agent_data_manager.api_mcp_gateway.vectorization_tool", MagicMock()), patch(
            "src.agent_data_manager.api_mcp_gateway.settings"
        ) as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch(
            "src.agent_data_manager.api_mcp_gateway.limiter"
        ) as mock_limiter:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            payload = {
                "query_text": "How to handle billing inquiries?",
                "customer_context": {
                    "customer_id": "CUST_12345",
                    "account_type": "premium",
                    "issue_category": "billing",
                },
                "metadata_filters": {"department": "customer_service"},
                "tags": ["billing", "inquiry"],
                "limit": 10,
                "score_threshold": 0.6,
            }

            response = client.post("/cskh_query", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert data["query_text"] == payload["query_text"]
            assert data["customer_context"] == payload["customer_context"]
            assert data["total_found"] == 1
            assert len(data["results"]) == 1
            assert "rag_info" in data
            assert "response_time_ms" in data
            assert data["cached"] is False

    @pytest.mark.asyncio
    async def test_cskh_query_performance_under_1s(self, client, mock_auth_disabled, mock_rag_search):
        """Test that CSKH queries complete under 1 second for performance requirement."""
        with patch("src.agent_data_manager.api_mcp_gateway.qdrant_rag_search", mock_rag_search), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store", AsyncMock()
        ), patch("src.agent_data_manager.api_mcp_gateway.vectorization_tool", MagicMock()), patch(
            "src.agent_data_manager.api_mcp_gateway.settings"
        ) as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch(
            "src.agent_data_manager.api_mcp_gateway.limiter"
        ) as mock_limiter:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            payload = {
                "query_text": "Customer service performance test query",
                "customer_context": {"customer_id": "PERF_TEST"},
                "limit": 5,
                "score_threshold": 0.7,
            }

            start_time = time.time()
            response = client.post("/cskh_query", json=payload)
            end_time = time.time()

            # Performance requirement: < 1 second
            assert (end_time - start_time) < 1.0
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["response_time_ms"] < 1000  # Less than 1000ms

    @pytest.mark.asyncio
    async def test_cskh_query_caching(self, client, mock_auth_disabled, mock_rag_search):
        """Test RAG caching functionality for performance optimization."""
        with patch("src.agent_data_manager.api_mcp_gateway.qdrant_rag_search", mock_rag_search), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store", AsyncMock()
        ), patch("src.agent_data_manager.api_mcp_gateway.vectorization_tool", MagicMock()), patch(
            "src.agent_data_manager.api_mcp_gateway.settings"
        ) as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch(
            "src.agent_data_manager.api_mcp_gateway.limiter"
        ) as mock_limiter:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            payload = {
                "query_text": "Cache test query for CSKH",
                "metadata_filters": {"category": "test"},
                "tags": ["cache_test"],
                "limit": 5,
            }

            # First request - should miss cache
            response1 = client.post("/cskh_query", json=payload)
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["cached"] is False

            # Second identical request - should hit cache
            response2 = client.post("/cskh_query", json=payload)
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["cached"] is True

            # Cache hit should be faster
            assert data2["response_time_ms"] <= data1["response_time_ms"]

    @pytest.mark.asyncio
    async def test_cskh_query_error_handling(self, client, mock_auth_disabled):
        """Test CSKH query error handling and metrics."""

        # Mock RAG search to fail
        async def failing_rag_search(*args, **kwargs):
            return {
                "status": "failed",
                "error": "Mock RAG search failure",
                "query": kwargs.get("query_text", ""),
                "results": [],
            }

        with patch("src.agent_data_manager.api_mcp_gateway.qdrant_rag_search", failing_rag_search), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store", AsyncMock()
        ), patch("src.agent_data_manager.api_mcp_gateway.vectorization_tool", MagicMock()), patch(
            "src.agent_data_manager.api_mcp_gateway.settings"
        ) as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch(
            "src.agent_data_manager.api_mcp_gateway.limiter"
        ) as mock_limiter:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            payload = {"query_text": "Error test query", "customer_context": {"customer_id": "ERROR_TEST"}}

            response = client.post("/cskh_query", json=payload)

            assert response.status_code == 200  # API should handle errors gracefully
            data = response.json()

            assert data["status"] == "error"
            assert data["total_found"] == 0
            assert len(data["results"]) == 0
            assert "error" in data
            assert data["message"] == "RAG search failed"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cskh_query_timeout_handling(self, client, mock_auth_disabled):
        """Test CSKH query timeout handling."""

        # Mock RAG search to timeout
        async def timeout_rag_search(*args, **kwargs):
            await asyncio.sleep(15)  # Longer than 10s timeout
            return {"status": "success", "results": []}

        with patch("src.agent_data_manager.api_mcp_gateway.qdrant_rag_search", timeout_rag_search), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store", AsyncMock()
        ), patch("src.agent_data_manager.api_mcp_gateway.vectorization_tool", MagicMock()), patch(
            "src.agent_data_manager.api_mcp_gateway.settings"
        ) as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch(
            "src.agent_data_manager.api_mcp_gateway.limiter"
        ) as mock_limiter:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            payload = {"query_text": "Timeout test query", "customer_context": {"customer_id": "TIMEOUT_TEST"}}

            response = client.post("/cskh_query", json=payload)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "error"
            assert "timeout" in data["error"].lower()
            assert data["message"] == "Query processing timed out"

    @pytest.mark.unit
    def test_cskh_query_validation(self, client, mock_auth_disabled):
        """Test CSKH query input validation."""
        with patch("src.agent_data_manager.api_mcp_gateway.settings") as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch("src.agent_data_manager.api_mcp_gateway.limiter") as mock_limiter:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            # Test missing required field
            payload = {
                "customer_context": {"customer_id": "VALIDATION_TEST"}
                # Missing query_text
            }

            response = client.post("/cskh_query", json=payload)
            assert response.status_code == 422  # Validation error

            # Test invalid score_threshold
            payload = {"query_text": "Validation test", "score_threshold": 1.5}  # Invalid: > 1.0

            response = client.post("/cskh_query", json=payload)
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_cskh_query_metrics_recording(self, client, mock_auth_disabled, mock_rag_search):
        """Test that CSKH query metrics are properly recorded."""
        with patch("src.agent_data_manager.api_mcp_gateway.qdrant_rag_search", mock_rag_search), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store", AsyncMock()
        ), patch("src.agent_data_manager.api_mcp_gateway.vectorization_tool", MagicMock()), patch(
            "src.agent_data_manager.api_mcp_gateway.settings"
        ) as mock_settings, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth, patch(
            "src.agent_data_manager.api_mcp_gateway.limiter"
        ) as mock_limiter, patch(
            "src.agent_data_manager.api_mcp_gateway.record_cskh_query"
        ) as mock_record_cskh, patch(
            "src.agent_data_manager.api_mcp_gateway.record_rag_search"
        ) as mock_record_rag, patch(
            "src.agent_data_manager.api_mcp_gateway.record_a2a_api_request"
        ) as mock_record_api:

            # Setup mocks
            mock_settings.ENABLE_AUTHENTICATION = False
            mock_auth.validate_user_access.return_value = True
            mock_limiter.limit.return_value = lambda func: func  # Disable rate limiting

            payload = {"query_text": "Metrics test query", "customer_context": {"customer_id": "METRICS_TEST"}}

            response = client.post("/cskh_query", json=payload)

            assert response.status_code == 200

            # Verify metrics were recorded
            mock_record_cskh.assert_called()
            mock_record_rag.assert_called()
            mock_record_api.assert_called()

            # Check that success metrics were recorded
            cskh_call_args = mock_record_cskh.call_args[0]
            assert cskh_call_args[0] == "success"  # status

            api_call_args = mock_record_api.call_args[0]
            assert api_call_args[0] == "cskh_query"  # endpoint
            assert api_call_args[1] == "success"  # status

    @pytest.mark.unit
    def test_api_root_includes_cskh_endpoint(self, client):
        """Test that the root endpoint includes the new CSKH endpoint."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "endpoints" in data
        assert "api" in data["endpoints"]
        assert "cskh_query" in data["endpoints"]["api"]
        assert data["endpoints"]["api"]["cskh_query"] == "/cskh_query"


