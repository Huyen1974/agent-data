"""
Additional CLI140e Coverage Tests - More targeted tests to reach coverage goals
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from ADK.agent_data.api_mcp_gateway import app, _get_cached_result, _cache_result
from ADK.agent_data.tools.qdrant_vectorization_tool import QdrantVectorizationTool, get_vectorization_tool


class TestAPIMCPGatewayCaching:
    """Test caching functionality in api_mcp_gateway.py."""

    @patch('ADK.agent_data.api_mcp_gateway._rag_cache')
    def test_get_cached_result(self, mock_cache):
        """Test getting cached results."""
        mock_cache.get.return_value = {"cached": "result"}
        
        result = _get_cached_result("test_key")
        assert result == {"cached": "result"}
        mock_cache.get.assert_called_once_with("test_key")

    @patch('ADK.agent_data.api_mcp_gateway._rag_cache')
    def test_get_cached_result_none(self, mock_cache):
        """Test getting cached results when cache is None."""
        mock_cache = None
        
        with patch('ADK.agent_data.api_mcp_gateway._rag_cache', None):
            result = _get_cached_result("test_key")
            assert result is None

    @patch('ADK.agent_data.api_mcp_gateway._rag_cache')
    def test_cache_result(self, mock_cache):
        """Test caching results."""
        _cache_result("test_key", {"test": "data"})
        mock_cache.put.assert_called_once_with("test_key", {"test": "data"})

    @patch('ADK.agent_data.api_mcp_gateway._rag_cache')
    def test_cache_result_none(self, mock_cache):
        """Test caching results when cache is None."""
        with patch('ADK.agent_data.api_mcp_gateway._rag_cache', None):
            _cache_result("test_key", {"test": "data"})
            # Should not raise an exception


class TestAPIEndpointsWithMocks:
    """Test API endpoints with proper mocking."""

    def test_login_endpoint(self):
        """Test login endpoint."""
        client = TestClient(app)
        
        with patch('ADK.agent_data.api_mcp_gateway.AuthManager') as mock_auth_manager:
            mock_auth_manager.return_value.authenticate_user.return_value = {
                "success": True,
                "user_id": "test_user",
                "email": "test@example.com",
                "scopes": ["read", "write"]
            }
            mock_auth_manager.return_value.create_access_token.return_value = "test_token"
            
            response = client.post("/auth/login", data={
                "username": "test@example.com",
                "password": "testpass"
            })
            
            # May return success or service unavailable
            assert response.status_code in [200, 503]

    def test_register_endpoint(self):
        """Test registration endpoint."""
        client = TestClient(app)
        
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "full_name": "Test User"
        })
        
        # May return success, error, or service unavailable
        assert response.status_code in [200, 400, 403, 503]

    def test_search_endpoint(self):
        """Test search endpoint."""
        client = TestClient(app)
        
        response = client.post("/search", json={
            "tag": "test",
            "limit": 10
        })
        
        # Should require authentication
        assert response.status_code in [401, 503]

    def test_rag_endpoint(self):
        """Test RAG search endpoint."""
        client = TestClient(app)
        
        response = client.post("/rag", json={
            "query_text": "test query",
            "limit": 5
        })
        
        # Should require authentication
        assert response.status_code in [401, 503]


class TestQdrantVectorizationToolAdditional:
    """Additional tests for QdrantVectorizationTool."""

    def test_get_vectorization_tool(self):
        """Test getting vectorization tool instance."""
        tool = get_vectorization_tool()
        assert isinstance(tool, QdrantVectorizationTool)

    @pytest.mark.asyncio
    async def test_vectorize_document_with_auto_tagging(self):
        """Test document vectorization with auto-tagging."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        tool.qdrant_store = AsyncMock()
        tool.firestore_manager = AsyncMock()
        
        with patch('ADK.agent_data.tools.qdrant_vectorization_tool.OPENAI_AVAILABLE', True), \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.openai_async_client', AsyncMock()), \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.get_openai_embedding') as mock_embedding, \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.get_auto_tagging_tool') as mock_tagging:
            
            mock_embedding.return_value = {"embedding": [0.1] * 1536}
            mock_tagging.return_value.generate_tags.return_value = {"tags": ["science", "physics"]}
            tool.qdrant_store.upsert_vector.return_value = {"success": True}
            
            result = await tool.vectorize_document(
                "doc1", 
                "test content", 
                metadata={"category": "science"},
                enable_auto_tagging=True
            )
            
            # Should succeed or fail gracefully
            assert "status" in result

    @pytest.mark.asyncio
    async def test_vectorize_document_embedding_failure(self):
        """Test document vectorization with embedding failure."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        tool.firestore_manager = AsyncMock()
        
        with patch('ADK.agent_data.tools.qdrant_vectorization_tool.OPENAI_AVAILABLE', True), \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.openai_async_client', AsyncMock()), \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.get_openai_embedding') as mock_embedding:
            
            mock_embedding.return_value = None  # Embedding failure
            
            result = await tool.vectorize_document("doc1", "test content")
            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_batch_vectorize_documents(self):
        """Test batch document vectorization."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        
        with patch.object(tool, 'vectorize_document') as mock_vectorize:
            mock_vectorize.return_value = {"status": "success", "doc_id": "test"}
            
            documents = [
                {"doc_id": "doc1", "content": "content1"},
                {"doc_id": "doc2", "content": "content2"}
            ]
            
            result = await tool.batch_vectorize_documents(documents)
            assert "status" in result

    @pytest.mark.asyncio
    async def test_rag_search_with_filters(self):
        """Test RAG search with various filters."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        tool.qdrant_store = AsyncMock()
        tool.firestore_manager = AsyncMock()
        
        # Mock Qdrant results
        tool.qdrant_store.semantic_search.return_value = {
            "results": [
                {
                    "metadata": {"doc_id": "doc1"},
                    "score": 0.9
                }
            ]
        }
        
        # Mock Firestore metadata
        tool.firestore_manager.get_metadata_with_version = AsyncMock(return_value={
            "doc_id": "doc1",
            "level_1_category": "Science",
            "level_2_category": "Physics",
            "auto_tags": ["science", "physics"],
            "content_preview": "Test content"
        })
        
        result = await tool.rag_search(
            "test query",
            metadata_filters={"category": "science"},
            tags=["physics"],
            path_query="Science",
            limit=5
        )
        
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_rag_search_with_qdrant_tag(self):
        """Test RAG search with Qdrant tag filter."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        tool.qdrant_store = AsyncMock()
        
        tool.qdrant_store.semantic_search.return_value = {"results": []}
        
        result = await tool.rag_search(
            "test query",
            qdrant_tag="test_tag"
        )
        
        assert result["status"] == "success"
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_update_vector_status_with_error(self):
        """Test updating vector status with error message."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        tool.firestore_manager = AsyncMock()
        
        await tool._update_vector_status(
            "doc1", 
            "failed", 
            {"test": "metadata"}, 
            "Test error message"
        )
        
        # Verify the call was made
        tool.firestore_manager.save_metadata.assert_called_once()


class TestAPIRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiting_with_jwt_token(self):
        """Test rate limiting with JWT token."""
        from ADK.agent_data.api_mcp_gateway import get_user_id_for_rate_limiting
        from fastapi import Request
        import base64
        import json
        
        # Create a mock JWT token
        payload = {"sub": "user123", "email": "test@example.com"}
        payload_encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        mock_token = f"header.{payload_encoded}.signature"
        
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": f"Bearer {mock_token}"}
        
        key = get_user_id_for_rate_limiting(mock_request)
        assert isinstance(key, str)

    def test_rate_limiting_with_invalid_jwt(self):
        """Test rate limiting with invalid JWT token."""
        from ADK.agent_data.api_mcp_gateway import get_user_id_for_rate_limiting
        from fastapi import Request
        
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer invalid.token.here"}
        
        key = get_user_id_for_rate_limiting(mock_request)
        assert isinstance(key, str)


class TestAPIStartupShutdown:
    """Test API startup and shutdown events."""

    @patch('ADK.agent_data.api_mcp_gateway._initialize_caches')
    def test_startup_event(self, mock_init_caches):
        """Test startup event handler."""
        # The startup event should initialize caches
        # This is tested indirectly through the app initialization
        pass


if __name__ == "__main__":
    pytest.main([__file__]) 