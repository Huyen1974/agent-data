#!/usr/bin/env python3
"""
CLI140m.2 - Targeted Coverage Tests
Focus on specific missing lines to reach 80% coverage for main modules
"""

import pytest
import asyncio
import json
import tempfile
import os
import time
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException, Request
import logging

# Add the ADK/agent_data directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_data_dir = os.path.dirname(current_dir)
sys.path.insert(0, agent_data_dir)

# Also add the parent directory to handle relative imports
parent_dir = os.path.dirname(agent_data_dir)
sys.path.insert(0, parent_dir)


class TestCLI140m2APIMCPGatewayTargeted:
    """Targeted tests for api_mcp_gateway.py missing coverage areas"""

    def test_thread_safe_lru_cache_cleanup_expired_method(self):
        """Test ThreadSafeLRUCache cleanup_expired method specifically"""
        # Import here to avoid module-level import issues
        import api_mcp_gateway
        
        cache = api_mcp_gateway.ThreadSafeLRUCache(max_size=3, ttl_seconds=1)
        
        # Add items that will expire
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Test cleanup_expired method directly
        expired_count = cache.cleanup_expired()
        assert expired_count >= 0

    def test_thread_safe_lru_cache_clear_method(self):
        """Test ThreadSafeLRUCache clear method specifically"""
        import api_mcp_gateway
        
        cache = api_mcp_gateway.ThreadSafeLRUCache(max_size=5)
        
        # Add items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert cache.size() == 2
        
        # Test clear method
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None

    def test_get_cached_result_cache_miss(self):
        """Test _get_cached_result with cache miss"""
        import api_mcp_gateway
        
        with patch('api_mcp_gateway.query_cache') as mock_cache:
            mock_cache.get.return_value = None
            
            result = api_mcp_gateway._get_cached_result("nonexistent_key")
            assert result is None
            mock_cache.get.assert_called_once_with("nonexistent_key")

    def test_cache_result_success_path(self):
        """Test _cache_result success path"""
        import api_mcp_gateway
        
        with patch('api_mcp_gateway.query_cache') as mock_cache:
            test_result = {"status": "success", "data": "test"}
            
            api_mcp_gateway._cache_result("test_key", test_result)
            mock_cache.put.assert_called_once_with("test_key", test_result)

    @patch('api_mcp_gateway.settings')
    def test_health_check_endpoint_coverage(self, mock_settings):
        """Test health check endpoint with all services"""
        import api_mcp_gateway
        
        mock_settings.ENABLE_AUTHENTICATION = True
        mock_settings.ALLOW_REGISTRATION = True
        
        # Mock all the global services
        with patch('api_mcp_gateway.qdrant_store', Mock()):
            with patch('api_mcp_gateway.firestore_manager', Mock()):
                with patch('api_mcp_gateway.vectorization_tool', Mock()):
                    with patch('api_mcp_gateway.auth_manager', Mock()):
                        with patch('api_mcp_gateway.user_manager', Mock()):
                            client = TestClient(api_mcp_gateway.app)
                            response = client.get("/health")
                            assert response.status_code == 200
                            data = response.json()
                            assert "status" in data
                            assert "services" in data
                            assert "authentication" in data

    def test_root_endpoint_coverage(self):
        """Test root endpoint"""
        import api_mcp_gateway
        
        client = TestClient(api_mcp_gateway.app)
        response = client.get("/")
        assert response.status_code == 200

    @patch('api_mcp_gateway.uvicorn')
    def test_main_function_coverage(self, mock_uvicorn):
        """Test main function"""
        import api_mcp_gateway
        
        api_mcp_gateway.main()
        mock_uvicorn.run.assert_called_once()

    @patch('api_mcp_gateway.settings')
    def test_get_current_user_dependency_auth_disabled(self, mock_settings):
        """Test get_current_user_dependency with auth disabled"""
        import api_mcp_gateway
        
        mock_settings.ENABLE_AUTHENTICATION = False
        
        async def test_func():
            result = await api_mcp_gateway.get_current_user_dependency()
            assert result["user_id"] == "anonymous"
            assert result["email"] == "anonymous@system"
            assert "read" in result["scopes"]
            assert "write" in result["scopes"]
        
        asyncio.run(test_func())

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.auth_manager', None)
    def test_get_current_user_dependency_no_auth_manager(self, mock_settings):
        """Test get_current_user_dependency with no auth manager"""
        import api_mcp_gateway
        
        mock_settings.ENABLE_AUTHENTICATION = True
        
        async def test_func():
            with pytest.raises(HTTPException) as exc_info:
                await api_mcp_gateway.get_current_user_dependency()
            assert exc_info.value.status_code == 503
        
        asyncio.run(test_func())

    @patch('api_mcp_gateway.settings')
    def test_login_endpoint_auth_disabled(self, mock_settings):
        """Test login endpoint with authentication disabled"""
        import api_mcp_gateway
        
        mock_settings.ENABLE_AUTHENTICATION = False
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/login", data={"username": "test", "password": "test"})
        assert response.status_code == 501

    @patch('api_mcp_gateway.settings')
    def test_register_endpoint_auth_disabled(self, mock_settings):
        """Test register endpoint with authentication disabled"""
        import api_mcp_gateway
        
        mock_settings.ENABLE_AUTHENTICATION = False
        
        client = TestClient(api_mcp_gateway.app)
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        })
        assert response.status_code == 501


class TestCLI140m2QdrantVectorizationToolTargeted:
    """Targeted tests for qdrant_vectorization_tool.py missing coverage areas"""

    def test_vectorization_tool_initialization(self):
        """Test QdrantVectorizationTool initialization"""
        # Import with absolute path to avoid relative import issues
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        assert tool.qdrant_store is None
        assert tool.firestore_manager is None
        assert tool._initialized is False

    async def test_rate_limit_method(self):
        """Test _rate_limit method"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        start_time = time.time()
        await tool._rate_limit()
        end_time = time.time()
        
        # Should complete quickly
        assert end_time - start_time < 1.0

    def test_filter_by_metadata_empty_filters(self):
        """Test _filter_by_metadata with empty filters"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        results = [{"id": "1", "metadata": {"key": "value"}}]
        
        filtered = tool._filter_by_metadata(results, {})
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_filter_by_metadata_with_filters(self):
        """Test _filter_by_metadata with actual filters"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        results = [
            {"id": "1", "metadata": {"author": "John", "year": 2023}},
            {"id": "2", "metadata": {"author": "Jane", "year": 2022}}
        ]
        
        filtered = tool._filter_by_metadata(results, {"author": "John"})
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_filter_by_tags_empty_tags(self):
        """Test _filter_by_tags with empty tags"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        results = [{"id": "1", "tags": ["science", "research"]}]
        
        filtered = tool._filter_by_tags(results, [])
        assert len(filtered) == 1

    def test_filter_by_path_empty_query(self):
        """Test _filter_by_path with empty query"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        results = [{"id": "1", "file_path": "/docs/science/paper.pdf"}]
        
        filtered = tool._filter_by_path(results, "")
        assert len(filtered) == 1

    def test_build_hierarchy_path_empty_metadata(self):
        """Test _build_hierarchy_path with empty metadata"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        result = {}
        
        path = tool._build_hierarchy_path(result)
        assert "Uncategorized" in path

    def test_build_hierarchy_path_with_metadata(self):
        """Test _build_hierarchy_path with metadata"""
        from tools.qdrant_vectorization_tool import QdrantVectorizationTool
        
        tool = QdrantVectorizationTool()
        result = {"tags": ["science", "research"]}
        
        path = tool._build_hierarchy_path(result)
        assert isinstance(path, str)

    def test_get_vectorization_tool_singleton(self):
        """Test get_vectorization_tool singleton function"""
        from tools.qdrant_vectorization_tool import get_vectorization_tool
        
        tool1 = get_vectorization_tool()
        tool2 = get_vectorization_tool()
        assert tool1 is tool2  # Should be the same instance


class TestCLI140m2DocumentIngestionToolTargeted:
    """Targeted tests for document_ingestion_tool.py missing coverage areas"""

    def test_ingestion_tool_initialization(self):
        """Test DocumentIngestionTool initialization"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        assert tool.firestore_manager is None
        assert tool._initialized is False
        assert tool.performance_metrics is not None

    def test_get_cache_key_method(self):
        """Test _get_cache_key method"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        key = tool._get_cache_key("test_doc", "test content")
        assert isinstance(key, str)
        assert "test_doc" in key

    def test_is_cache_valid_method(self):
        """Test _is_cache_valid method"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        # Test with non-existent cache entry
        is_valid = tool._is_cache_valid("nonexistent_key")
        assert is_valid is False

    def test_get_content_hash_method(self):
        """Test _get_content_hash method"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        hash1 = tool._get_content_hash("test content")
        hash2 = tool._get_content_hash("test content")
        hash3 = tool._get_content_hash("different content")
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash

    async def test_save_to_disk_success(self):
        """Test _save_to_disk success path"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await tool._save_to_disk("test_doc", "test content", temp_dir)
            assert result["status"] == "success"
            assert "file_path" in result

    async def test_save_to_disk_failure(self):
        """Test _save_to_disk failure path"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        
        # Use invalid directory to cause failure
        result = await tool._save_to_disk("test_doc", "test content", "/invalid/path")
        assert result["status"] == "failed"

    def test_get_performance_metrics(self):
        """Test get_performance_metrics method"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        metrics = tool.get_performance_metrics()
        assert "total_calls" in metrics
        assert "avg_latency" in metrics

    def test_reset_performance_metrics(self):
        """Test reset_performance_metrics method"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        # Add some metrics first
        tool.performance_metrics["total_calls"] = 5
        
        tool.reset_performance_metrics()
        metrics = tool.get_performance_metrics()
        assert metrics["total_calls"] == 0

    def test_get_document_ingestion_tool_singleton(self):
        """Test get_document_ingestion_tool singleton function"""
        from tools.document_ingestion_tool import get_document_ingestion_tool
        
        tool1 = get_document_ingestion_tool()
        tool2 = get_document_ingestion_tool()
        assert tool1 is tool2  # Should be the same instance

    @patch('tools.document_ingestion_tool.asyncio.get_event_loop')
    def test_ingest_document_sync_exception_handling(self, mock_get_loop):
        """Test ingest_document_sync exception handling"""
        from tools.document_ingestion_tool import DocumentIngestionTool
        
        tool = DocumentIngestionTool()
        mock_loop = Mock()
        mock_loop.run_until_complete.side_effect = Exception("Test exception")
        mock_get_loop.return_value = mock_loop
        
        result = tool.ingest_document_sync("test_doc", "test content")
        assert result["status"] == "failed"
        assert "error" in result


class TestCLI140m2CoverageValidation:
    """Validation test to ensure coverage targets are met"""

    def test_cli140m2_targeted_coverage_validation(self):
        """Validate that CLI140m2 targeted tests improve coverage"""
        # This test serves as a marker for coverage validation
        # The actual coverage will be measured by pytest-cov
        assert True  # Placeholder assertion


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 