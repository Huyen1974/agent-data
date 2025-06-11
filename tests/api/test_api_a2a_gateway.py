"""
Test suite for API A2A Gateway endpoints
Tests /save, /query, /search endpoints for agent-to-agent communication
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os

# Import the FastAPI app
from agent_data_manager.api_mcp_gateway import app, SaveDocumentRequest, QueryVectorsRequest, SearchDocumentsRequest
from fastapi.testclient import TestClient
from fastapi import Depends


class TestAPIAGateway:
    """Test class for API A2A Gateway endpoints"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with disabled authentication"""
        # Disable authentication for tests
        with patch.dict(os.environ, {"ENABLE_AUTHENTICATION": "false"}):
            yield

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app"""
        # Mock the startup event dependencies and override authentication
        with patch("agent_data_manager.api_mcp_gateway.settings.ENABLE_AUTHENTICATION", False):
            with patch("agent_data_manager.api_mcp_gateway.auth_manager", None):
                with patch("agent_data_manager.api_mcp_gateway.user_manager", None):
                    # Override the get_current_user dependency to return a mock user
                    def mock_get_current_user():
                        return {"user_id": "test_user_123", "email": "test@example.com", "scopes": ["read", "write"]}

                    app.dependency_overrides[app.dependencies[0] if hasattr(app, "dependencies") else None] = (
                        mock_get_current_user
                    )

                    # Override the dependency directly
                    from agent_data_manager.api_mcp_gateway import get_current_user

                    app.dependency_overrides[get_current_user] = mock_get_current_user

                    try:
                        yield TestClient(app)
                    finally:
                        # Clean up dependency overrides
                        app.dependency_overrides.clear()

    @pytest.fixture
    def authenticated_client(self):
        """Create test client with mocked authentication"""
        # Mock authentication dependencies
        mock_auth_manager = MagicMock()
        mock_user_manager = MagicMock()

        with patch("agent_data_manager.api_mcp_gateway.auth_manager", mock_auth_manager):
            with patch("agent_data_manager.api_mcp_gateway.user_manager", mock_user_manager):
                with patch("agent_data_manager.api_mcp_gateway.get_current_user") as mock_get_user:
                    mock_get_user.return_value = {
                        "user_id": "test_user_123",
                        "email": "test@example.com",
                        "scopes": ["read", "write"],
                    }
                    return TestClient(app)

    @pytest.fixture
    def mock_vectorization_tool(self):
        """Mock QdrantVectorizationTool"""
        mock = AsyncMock()
        mock.vectorize_document.return_value = {
            "status": "success",
            "doc_id": "test_doc_001",
            "vector_id": "vec_001",
            "embedding_dimension": 1536,
            "metadata_keys": ["doc_id", "content_preview", "vectorized_at"],
        }
        return mock

    @pytest.fixture
    def mock_qdrant_store(self):
        """Mock QdrantStore"""
        mock = AsyncMock()
        mock.semantic_search.return_value = {
            "results": [
                {
                    "id": "doc_001",
                    "score": 0.95,
                    "metadata": {"doc_id": "doc_001", "content_preview": "Test document..."},
                    "vector": [0.1, 0.2, 0.3],  # Truncated for testing
                }
            ],
            "query_text": "test query",
        }
        mock.query_vectors_by_tag.return_value = {
            "results": [
                {"id": "doc_002", "metadata": {"doc_id": "doc_002", "tag": "test_tag"}, "vector": [0.4, 0.5, 0.6]}
            ]
        }
        return mock

    @pytest.fixture
    def sample_save_request(self):
        """Sample document save request"""
        return {
            "doc_id": "api_test_doc_001",
            "content": "This is a test document for API A2A gateway validation.",
            "metadata": {"source": "test_agent", "priority": "normal", "test_case": "api_a2a_validation"},
            "tag": "api_testing",
            "update_firestore": True,
        }

    @pytest.fixture
    def sample_query_request(self):
        """Sample semantic query request"""
        return {
            "query_text": "How to reset password for user account",
            "tag": "customer_support",
            "limit": 5,
            "score_threshold": 0.8,
        }

    @pytest.fixture
    def sample_search_request(self):
        """Sample document search request"""
        return {"tag": "api_testing", "limit": 10, "offset": 0, "include_vectors": False}

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "Agent Data API A2A Gateway"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "timestamp" in data

        # Check required endpoints are listed
        endpoints = data["endpoints"]
        assert "/health" in str(endpoints.values())
        assert "/save" in str(endpoints.values())
        assert "/query" in str(endpoints.values())
        assert "/search" in str(endpoints.values())

    def test_health_endpoint_no_services(self, client):
        """Test health endpoint when no services are initialized"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["version"] == "1.0.0"
        assert "services" in data
        assert "timestamp" in data

        # Should be degraded when services aren't connected
        services = data["services"]
        assert services["qdrant"] == "disconnected"
        assert services["firestore"] == "disconnected"
        assert services["vectorization"] == "unavailable"

    def test_save_document_success(self, client, sample_save_request):
        """Test successful document save via API A2A"""
        with patch("agent_data_manager.api_mcp_gateway.vectorization_tool") as mock_tool:
            # Setup async mock
            mock_tool.vectorize_document = AsyncMock(
                return_value={
                    "status": "success",
                    "doc_id": "api_test_doc_001",
                    "vector_id": "vec_001",
                    "embedding_dimension": 1536,
                }
            )

            response = client.post("/save", json=sample_save_request)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["doc_id"] == sample_save_request["doc_id"]
            assert "message" in data
            assert data["firestore_updated"] is True

    @pytest.mark.deferred
    @patch("agent_data_manager.api_mcp_gateway.vectorization_tool", None)
    def test_save_document_service_unavailable(self, client, sample_save_request):
        """Test save document when vectorization service is unavailable"""
        response = client.post("/save", json=sample_save_request)
        assert response.status_code == 503
        assert "Vectorization service unavailable" in response.json()["detail"]

    @pytest.mark.deferred
    def test_save_document_invalid_request(self, client):
        """Test save document with invalid request data"""
        with patch("agent_data_manager.api_mcp_gateway.vectorization_tool") as mock_tool:
            # Mock the tool to be available
            mock_tool.vectorize_document = AsyncMock()

            invalid_request = {"doc_id": "", "content": "Test content"}  # Empty doc_id should fail validation

            response = client.post("/save", json=invalid_request)
            assert response.status_code == 422  # Unprocessable Entity for validation errors

    def test_query_vectors_success(self, client, sample_query_request):
        """Test successful semantic query via API A2A"""
        with patch("agent_data_manager.api_mcp_gateway.qdrant_store") as mock_store:
            # Setup async mock
            mock_store.semantic_search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": "doc_001",
                            "score": 0.95,
                            "metadata": {"doc_id": "doc_001", "content_preview": "Test document..."},
                        }
                    ]
                }
            )

            response = client.post("/query", json=sample_query_request)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["query_text"] == sample_query_request["query_text"]
            assert "results" in data
            assert "total_found" in data

    @pytest.mark.deferred
    @patch("agent_data_manager.api_mcp_gateway.qdrant_store", None)
    def test_query_vectors_service_unavailable(self, client, sample_query_request):
        """Test query vectors when Qdrant service is unavailable"""
        response = client.post("/query", json=sample_query_request)
        assert response.status_code == 503
        assert "Qdrant service unavailable" in response.json()["detail"]

    @pytest.mark.deferred
    def test_query_vectors_invalid_request(self, client):
        """Test query vectors with invalid request data"""
        invalid_request = {
            "query_text": "",  # Empty query should fail validation
            "limit": 150,  # Exceeds maximum limit
        }

        response = client.post("/query", json=invalid_request)
        assert response.status_code == 422

    def test_search_documents_success(self, client, sample_search_request):
        """Test successful document search via API A2A"""
        with patch("agent_data_manager.api_mcp_gateway.qdrant_store") as mock_store:
            # Setup async mock
            mock_store.query_vectors_by_tag = AsyncMock(
                return_value={"results": [{"id": "doc_002", "metadata": {"doc_id": "doc_002", "tag": "api_testing"}}]}
            )

            response = client.post("/search", json=sample_search_request)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "results" in data
            assert "total_found" in data

    @pytest.mark.deferred
    @patch("agent_data_manager.api_mcp_gateway.qdrant_store", None)
    def test_search_documents_service_unavailable(self, client, sample_search_request):
        """Test search documents when Qdrant service is unavailable"""
        response = client.post("/search", json=sample_search_request)
        assert response.status_code == 503
        assert "Qdrant service unavailable" in response.json()["detail"]

    @pytest.mark.deferred
    def test_search_documents_with_vectors(self, client):
        """Test search documents including vector embeddings"""
        request_with_vectors = {"tag": "test_tag", "limit": 5, "offset": 0, "include_vectors": True}

        with patch("agent_data_manager.api_mcp_gateway.qdrant_store") as mock_qdrant_store:
            mock_qdrant_store.query_vectors_by_tag = AsyncMock(
                return_value={
                    "results": [{"id": "doc_001", "metadata": {"doc_id": "doc_001"}, "vector": [0.1, 0.2, 0.3]}]
                }
            )

            response = client.post("/search", json=request_with_vectors)
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert "results" in data

    @pytest.mark.deferred
    def test_pydantic_models_validation(self):
        """Test Pydantic model validation for API requests"""
        # Test SaveDocumentRequest validation
        valid_save_request = SaveDocumentRequest(
            doc_id="test_doc", content="Test content", metadata={"key": "value"}, tag="test"
        )
        assert valid_save_request.doc_id == "test_doc"

        # Test QueryVectorsRequest validation
        valid_query_request = QueryVectorsRequest(query_text="test query", limit=5)
        assert valid_query_request.query_text == "test query"
        assert valid_query_request.limit == 5

        # Test SearchDocumentsRequest validation
        valid_search_request = SearchDocumentsRequest(tag="test", limit=10, offset=0)
        assert valid_search_request.tag == "test"
        assert valid_search_request.limit == 10

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_api_a2a_integration_flow(self):
        """Integration test for complete API A2A flow: save -> query -> search"""
        # This test simulates the complete agent-to-agent communication flow
        test_doc_id = "integration_test_doc_001"
        test_content = "This is an integration test document for API A2A gateway."
        test_tag = "integration_testing"

        # Mock the entire flow
        with patch("agent_data_manager.api_mcp_gateway.vectorization_tool") as mock_vectorization, patch(
            "agent_data_manager.api_mcp_gateway.qdrant_store"
        ) as mock_qdrant:

            # Setup async mocks
            mock_vectorization.vectorize_document = AsyncMock(
                return_value={
                    "status": "success",
                    "doc_id": test_doc_id,
                    "vector_id": "vec_001",
                    "embedding_dimension": 1536,
                }
            )

            mock_qdrant.semantic_search = AsyncMock(
                return_value={
                    "results": [
                        {
                            "id": test_doc_id,
                            "score": 0.95,
                            "metadata": {"doc_id": test_doc_id, "content_preview": test_content[:50]},
                        }
                    ]
                }
            )

            mock_qdrant.query_vectors_by_tag = AsyncMock(
                return_value={"results": [{"id": test_doc_id, "metadata": {"doc_id": test_doc_id, "tag": test_tag}}]}
            )

            # Disable authentication for this test
            with patch("agent_data_manager.api_mcp_gateway.settings.ENABLE_AUTHENTICATION", False):
                # Override the get_current_user dependency
                def mock_get_current_user():
                    return {"user_id": "test_user_123", "email": "test@example.com", "scopes": ["read", "write"]}

                from agent_data_manager.api_mcp_gateway import get_current_user

                app.dependency_overrides[get_current_user] = mock_get_current_user

                try:
                    client = TestClient(app)

                    # Step 1: Save document
                    save_request = {
                        "doc_id": test_doc_id,
                        "content": test_content,
                        "tag": test_tag,
                        "metadata": {"test_type": "integration"},
                    }
                    save_response = client.post("/save", json=save_request)
                    assert save_response.status_code == 200

                    save_data = save_response.json()
                    assert save_data["status"] == "success"
                    assert save_data["doc_id"] == test_doc_id

                    # Step 2: Query for similar documents
                    query_request = {"query_text": test_content, "tag": test_tag, "limit": 5}
                    query_response = client.post("/query", json=query_request)
                    assert query_response.status_code == 200

                    query_data = query_response.json()
                    assert query_data["status"] == "success"
                    assert len(query_data["results"]) > 0

                    # Step 3: Search documents by tag
                    search_request = {"tag": test_tag, "limit": 10, "offset": 0}
                    search_response = client.post("/search", json=search_request)
                    assert search_response.status_code == 200

                    search_data = search_response.json()
                    assert search_data["status"] == "success"
                    assert len(search_data["results"]) > 0
                finally:
                    # Clean up dependency overrides
                    app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
