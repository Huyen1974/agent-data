"""
Test CLI 139: API Error Handling and Performance Improvements

Tests for enhanced error handling in A2A API endpoints (/batch_save, /batch_query)
with retry logic, timeout handling, and detailed error reporting.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.agent_data_manager.api_mcp_gateway import app, RateLimitError, ValidationError, ServerError, TimeoutError


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user for testing."""
    return {"user_id": "test_user_123", "email": "test@example.com", "scopes": ["read", "write"]}


class TestCLI139APIErrorHandling:
    """Test suite for CLI 139 API error handling and performance improvements."""

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_batch_save_retry_logic_on_rate_limit(self, client, mock_auth_user):
        """Test that batch_save retries on rate limit errors with exponential backoff."""

        # Mock dependencies
        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            # Setup mocks
            mock_auth.validate_user_access.return_value = True

            # Simulate rate limit error on first call, success on retry
            mock_vectorization.vectorize_document = AsyncMock()
            mock_vectorization.vectorize_document.side_effect = [
                {"status": "failed", "error": "rate limit exceeded"},
                {"status": "success", "vector_id": "vec_123", "embedding_dimension": 1536},
            ]

            # Test data
            test_data = {
                "documents": [
                    {"doc_id": "test_doc_1", "content": "Test content for rate limit retry", "metadata": {"test": True}}
                ]
            }

            start_time = time.time()

            # Make request
            response = client.post("/batch_save", json=test_data, headers={"Authorization": "Bearer test_token"})

            end_time = time.time()

            # Verify response
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["successful_saves"] == 1
            assert result["failed_saves"] == 0

            # Verify retry was attempted (should take some time due to backoff)
            assert end_time - start_time >= 0.5  # At least 0.5s for retry backoff

            # Verify vectorization was called twice (initial + retry)
            assert mock_vectorization.vectorize_document.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_batch_query_timeout_handling(self, client, mock_auth_user):
        """Test that batch_query handles timeouts properly."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store"
        ) as mock_qdrant, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            # Setup mocks
            mock_auth.validate_user_access.return_value = True

            # Simulate timeout
            async def slow_search(*args, **kwargs):
                await asyncio.sleep(20)  # Longer than 15s timeout
                return {"results": []}

            mock_qdrant.semantic_search = slow_search

            # Test data
            test_data = {"queries": [{"query_text": "test query that will timeout", "limit": 5}]}

            start_time = time.time()

            # Make request
            response = client.post("/batch_query", json=test_data, headers={"Authorization": "Bearer test_token"})

            end_time = time.time()

            # Verify response
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["failed_queries"] == 1
            assert result["successful_queries"] == 0

            # Verify timeout occurred (should be around 15s, not 20s)
            assert 14 <= end_time - start_time <= 17

            # Check error details
            assert len(result["results"]) == 1
            assert result["results"][0]["status"] == "error"
            assert "timeout" in result["results"][0]["error"].lower()

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_error_categorization_and_reporting(self, client, mock_auth_user):
        """Test that errors are properly categorized and reported with detailed messages."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            # Setup mocks
            mock_auth.validate_user_access.return_value = True

            # Test different error types
            error_scenarios = [
                {"status": "failed", "error": "rate limit exceeded - quota exhausted"},
                {"status": "failed", "error": "validation failed - invalid content format"},
                {"status": "failed", "error": "server error - internal processing failed"},
            ]

            mock_vectorization.vectorize_document = AsyncMock()
            mock_vectorization.vectorize_document.side_effect = error_scenarios

            # Test data with multiple documents
            test_data = {
                "documents": [
                    {"doc_id": f"test_doc_{i}", "content": f"Test content {i}", "metadata": {}} for i in range(3)
                ]
            }

            # Make request
            response = client.post("/batch_save", json=test_data, headers={"Authorization": "Bearer test_token"})

            # Verify response
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["failed_saves"] == 3
            assert result["successful_saves"] == 0

            # Verify error categorization
            errors = [r["error"] for r in result["results"]]
            assert any("RateLimitError" in error for error in errors)
            assert any("ValidationError" in error for error in errors)
            assert any("ServerError" in error for error in errors)

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_batch_operations_performance_under_5_seconds(self, client, mock_auth_user):
        """Test that batch operations complete within 5 seconds for reasonable loads."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.qdrant_store") as mock_qdrant, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth:

            # Setup mocks for fast responses
            mock_auth.validate_user_access.return_value = True

            # Fast vectorization mock
            async def fast_vectorize(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate 100ms processing
                return {"status": "success", "vector_id": "vec_123", "embedding_dimension": 1536}

            mock_vectorization.vectorize_document = fast_vectorize

            # Fast search mock
            async def fast_search(*args, **kwargs):
                await asyncio.sleep(0.05)  # Simulate 50ms search
                return {"results": [{"id": "doc_1", "score": 0.9, "payload": {"content": "test"}}]}

            mock_qdrant.semantic_search = fast_search

            # Test batch save performance
            save_data = {
                "documents": [
                    {"doc_id": f"perf_doc_{i}", "content": f"Performance test content {i}", "metadata": {}}
                    for i in range(10)  # 10 documents
                ]
            }

            start_time = time.time()
            save_response = client.post("/batch_save", json=save_data, headers={"Authorization": "Bearer test_token"})
            save_time = time.time() - start_time

            # Test batch query performance
            query_data = {
                "queries": [{"query_text": f"performance test query {i}", "limit": 5} for i in range(10)]  # 10 queries
            }

            start_time = time.time()
            query_response = client.post(
                "/batch_query", json=query_data, headers={"Authorization": "Bearer test_token"}
            )
            query_time = time.time() - start_time

            # Verify performance
            assert save_response.status_code == 200
            assert query_response.status_code == 200
            assert save_time < 5.0, f"Batch save took {save_time:.2f}s, should be < 5s"
            assert query_time < 5.0, f"Batch query took {query_time:.2f}s, should be < 5s"

            # Verify successful operations
            save_result = save_response.json()
            query_result = query_response.json()
            assert save_result["successful_saves"] == 10
            assert query_result["successful_queries"] == 10

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_concurrent_session_operations(self):
        """Test concurrent session operations with optimistic locking."""

        from src.agent_data_manager.session.session_manager import SessionManager

        with patch("src.agent_data_manager.session.session_manager.FirestoreMetadataManager") as mock_firestore:

            # Mock session data
            session_data = {"session_id": "test_session", "state": {"counter": 0}, "version": 1, "lock_timestamp": None}

            mock_firestore_instance = AsyncMock()
            mock_firestore.return_value = mock_firestore_instance
            mock_firestore_instance.get_metadata.return_value = session_data
            mock_firestore_instance.save_metadata = AsyncMock()

            session_manager = SessionManager()
            await session_manager._ensure_initialized()

            # Test concurrent updates
            async def update_counter(session_id, increment):
                return await session_manager.update_session_state_with_optimistic_locking(
                    session_id, {"counter": session_data["state"]["counter"] + increment}
                )

            # Simulate concurrent updates
            tasks = [
                update_counter("test_session", 1),
                update_counter("test_session", 2),
                update_counter("test_session", 3),
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Verify at least one succeeded
            successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
            assert len(successful_results) >= 1

            # Verify operation completed quickly (with retries)
            assert end_time - start_time < 2.0  # Should complete within 2 seconds

            # Verify save_metadata was called multiple times (original + retries)
            assert mock_firestore_instance.save_metadata.call_count >= 3

    @pytest.mark.deferred
    def test_api_error_classes_defined(self):
        """Test that custom error classes are properly defined."""

        # Test error class hierarchy
        assert issubclass(RateLimitError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(ServerError, Exception)
        assert issubclass(TimeoutError, Exception)

        # Test error instantiation
        rate_limit_error = RateLimitError("Rate limit exceeded")
        validation_error = ValidationError("Invalid input")
        server_error = ServerError("Internal server error")
        timeout_error = TimeoutError("Operation timed out")

        assert str(rate_limit_error) == "Rate limit exceeded"
        assert str(validation_error) == "Invalid input"
        assert str(server_error) == "Internal server error"
        assert str(timeout_error) == "Operation timed out"


@pytest.mark.integration
class TestCLI139Integration:
    """Integration tests for CLI 139 improvements."""

    @pytest.mark.asyncio
    async def test_end_to_end_error_recovery(self, client, mock_auth_user):
        """Test end-to-end error recovery scenario."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            mock_auth.validate_user_access.return_value = True

            # Simulate failure then success scenario
            call_count = 0

            async def variable_response(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"status": "failed", "error": "rate limit exceeded"}
                else:
                    return {"status": "success", "vector_id": "vec_123", "embedding_dimension": 1536}

            mock_vectorization.vectorize_document = variable_response

            test_data = {
                "documents": [
                    {
                        "doc_id": "recovery_test_doc",
                        "content": "Test content for error recovery",
                        "metadata": {"test_type": "error_recovery"},
                    }
                ]
            }

            # Make request
            response = client.post("/batch_save", json=test_data, headers={"Authorization": "Bearer test_token"})

            # Verify successful recovery
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["successful_saves"] == 1
            assert result["failed_saves"] == 0

            # Verify retry occurred
            assert call_count == 2


@pytest.mark.deferred
class TestCLI139:
    """Deferred tests for CLI 139 improvements."""

    @pytest.mark.asyncio
    async def test_batch_save_retry_logic_on_rate_limit(self, client, mock_auth_user):
        """Test that batch_save retries on rate limit errors with exponential backoff."""

        # Mock dependencies
        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            # Setup mocks
            mock_auth.validate_user_access.return_value = True

            # Simulate rate limit error on first call, success on retry
            mock_vectorization.vectorize_document = AsyncMock()
            mock_vectorization.vectorize_document.side_effect = [
                {"status": "failed", "error": "rate limit exceeded"},
                {"status": "success", "vector_id": "vec_123", "embedding_dimension": 1536},
            ]

            # Test data
            test_data = {
                "documents": [
                    {"doc_id": "test_doc_1", "content": "Test content for rate limit retry", "metadata": {"test": True}}
                ]
            }

            start_time = time.time()

            # Make request
            response = client.post("/batch_save", json=test_data, headers={"Authorization": "Bearer test_token"})

            end_time = time.time()

            # Verify response
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["successful_saves"] == 1
            assert result["failed_saves"] == 0

            # Verify retry was attempted (should take some time due to backoff)
            assert end_time - start_time >= 0.5  # At least 0.5s for retry backoff

            # Verify vectorization was called twice (initial + retry)
            assert mock_vectorization.vectorize_document.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_query_timeout_handling(self, client, mock_auth_user):
        """Test that batch_query handles timeouts properly."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.qdrant_store"
        ) as mock_qdrant, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            # Setup mocks
            mock_auth.validate_user_access.return_value = True

            # Simulate timeout
            async def slow_search(*args, **kwargs):
                await asyncio.sleep(20)  # Longer than 15s timeout
                return {"results": []}

            mock_qdrant.semantic_search = slow_search

            # Test data
            test_data = {"queries": [{"query_text": "test query that will timeout", "limit": 5}]}

            start_time = time.time()

            # Make request
            response = client.post("/batch_query", json=test_data, headers={"Authorization": "Bearer test_token"})

            end_time = time.time()

            # Verify response
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["failed_queries"] == 1
            assert result["successful_queries"] == 0

            # Verify timeout occurred (should be around 15s, not 20s)
            assert 14 <= end_time - start_time <= 17

            # Check error details
            assert len(result["results"]) == 1
            assert result["results"][0]["status"] == "error"
            assert "timeout" in result["results"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_error_categorization_and_reporting(self, client, mock_auth_user):
        """Test that errors are properly categorized and reported with detailed messages."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            # Setup mocks
            mock_auth.validate_user_access.return_value = True

            # Test different error types
            error_scenarios = [
                {"status": "failed", "error": "rate limit exceeded - quota exhausted"},
                {"status": "failed", "error": "validation failed - invalid content format"},
                {"status": "failed", "error": "server error - internal processing failed"},
            ]

            mock_vectorization.vectorize_document = AsyncMock()
            mock_vectorization.vectorize_document.side_effect = error_scenarios

            # Test data with multiple documents
            test_data = {
                "documents": [
                    {"doc_id": f"test_doc_{i}", "content": f"Test content {i}", "metadata": {}} for i in range(3)
                ]
            }

            # Make request
            response = client.post("/batch_save", json=test_data, headers={"Authorization": "Bearer test_token"})

            # Verify response
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["failed_saves"] == 3
            assert result["successful_saves"] == 0

            # Verify error categorization
            errors = [r["error"] for r in result["results"]]
            assert any("RateLimitError" in error for error in errors)
            assert any("ValidationError" in error for error in errors)
            assert any("ServerError" in error for error in errors)

    @pytest.mark.asyncio
    async def test_batch_operations_performance_under_5_seconds(self, client, mock_auth_user):
        """Test that batch operations complete within 5 seconds for reasonable loads."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.qdrant_store") as mock_qdrant, patch(
            "src.agent_data_manager.api_mcp_gateway.auth_manager"
        ) as mock_auth:

            # Setup mocks for fast responses
            mock_auth.validate_user_access.return_value = True

            # Fast vectorization mock
            async def fast_vectorize(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate 100ms processing
                return {"status": "success", "vector_id": "vec_123", "embedding_dimension": 1536}

            mock_vectorization.vectorize_document = fast_vectorize

            # Fast search mock
            async def fast_search(*args, **kwargs):
                await asyncio.sleep(0.05)  # Simulate 50ms search
                return {"results": [{"id": "doc_1", "score": 0.9, "payload": {"content": "test"}}]}

            mock_qdrant.semantic_search = fast_search

            # Test batch save performance
            save_data = {
                "documents": [
                    {"doc_id": f"perf_doc_{i}", "content": f"Performance test content {i}", "metadata": {}}
                    for i in range(10)  # 10 documents
                ]
            }

            start_time = time.time()
            save_response = client.post("/batch_save", json=save_data, headers={"Authorization": "Bearer test_token"})
            save_time = time.time() - start_time

            # Test batch query performance
            query_data = {
                "queries": [{"query_text": f"performance test query {i}", "limit": 5} for i in range(10)]  # 10 queries
            }

            start_time = time.time()
            query_response = client.post(
                "/batch_query", json=query_data, headers={"Authorization": "Bearer test_token"}
            )
            query_time = time.time() - start_time

            # Verify performance
            assert save_response.status_code == 200
            assert query_response.status_code == 200
            assert save_time < 5.0, f"Batch save took {save_time:.2f}s, should be < 5s"
            assert query_time < 5.0, f"Batch query took {query_time:.2f}s, should be < 5s"

            # Verify successful operations
            save_result = save_response.json()
            query_result = query_response.json()
            assert save_result["successful_saves"] == 10
            assert query_result["successful_queries"] == 10

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self):
        """Test concurrent session operations with optimistic locking."""

        from src.agent_data_manager.session.session_manager import SessionManager

        with patch("src.agent_data_manager.session.session_manager.FirestoreMetadataManager") as mock_firestore:

            # Mock session data
            session_data = {"session_id": "test_session", "state": {"counter": 0}, "version": 1, "lock_timestamp": None}

            mock_firestore_instance = AsyncMock()
            mock_firestore.return_value = mock_firestore_instance
            mock_firestore_instance.get_metadata.return_value = session_data
            mock_firestore_instance.save_metadata = AsyncMock()

            session_manager = SessionManager()
            await session_manager._ensure_initialized()

            # Test concurrent updates
            async def update_counter(session_id, increment):
                return await session_manager.update_session_state_with_optimistic_locking(
                    session_id, {"counter": session_data["state"]["counter"] + increment}
                )

            # Simulate concurrent updates
            tasks = [
                update_counter("test_session", 1),
                update_counter("test_session", 2),
                update_counter("test_session", 3),
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Verify at least one succeeded
            successful_results = [r for r in results if isinstance(r, dict) and r.get("status") == "success"]
            assert len(successful_results) >= 1

            # Verify operation completed quickly (with retries)
            assert end_time - start_time < 2.0  # Should complete within 2 seconds

            # Verify save_metadata was called multiple times (original + retries)
            assert mock_firestore_instance.save_metadata.call_count >= 3

    @pytest.mark.asyncio
    async def test_end_to_end_error_recovery(self, client, mock_auth_user):
        """Test end-to-end error recovery scenario."""

        with patch("src.agent_data_manager.api_mcp_gateway.get_current_user", return_value=mock_auth_user), patch(
            "src.agent_data_manager.api_mcp_gateway.vectorization_tool"
        ) as mock_vectorization, patch("src.agent_data_manager.api_mcp_gateway.auth_manager") as mock_auth:

            mock_auth.validate_user_access.return_value = True

            # Simulate failure then success scenario
            call_count = 0

            async def variable_response(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"status": "failed", "error": "rate limit exceeded"}
                else:
                    return {"status": "success", "vector_id": "vec_123", "embedding_dimension": 1536}

            mock_vectorization.vectorize_document = variable_response

            test_data = {
                "documents": [
                    {
                        "doc_id": "recovery_test_doc",
                        "content": "Test content for error recovery",
                        "metadata": {"test_type": "error_recovery"},
                    }
                ]
            }

            # Make request
            response = client.post("/batch_save", json=test_data, headers={"Authorization": "Bearer test_token"})

            # Verify successful recovery
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "completed"
            assert result["successful_saves"] == 1
            assert result["failed_saves"] == 0

            # Verify retry occurred
            assert call_count == 2
