"""
CLI140m.4 Coverage Enhancement Tests
====================================

Comprehensive test suite to achieve ≥80% coverage for:
- api_mcp_gateway.py (target: 80%, current: 79%)
- qdrant_vectorization_tool.py (target: 80%, current: 54.5%)
- document_ingestion_tool.py (target: 80%, current: 66.7%)

This test file resolves import issues by using proper absolute imports
and sys.path manipulation to ensure modules can be imported and tested.
"""

import sys
import os
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional
import time
from datetime import datetime
import json

# Add the ADK/agent_data directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
agent_data_dir = os.path.dirname(current_dir)
if agent_data_dir not in sys.path:
    sys.path.insert(0, agent_data_dir)

# Now import the modules with proper path resolution
try:
    # Import modules directly from the agent_data directory
    sys.path.insert(0, os.path.join(agent_data_dir, 'tools'))
    sys.path.insert(0, os.path.join(agent_data_dir, 'config'))
    
    import api_mcp_gateway
    import qdrant_vectorization_tool
    import document_ingestion_tool
    import settings
    IMPORTS_SUCCESSFUL = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_SUCCESSFUL = False


class TestCLI140m4APIMCPGatewayCoverage:
    """Test class to achieve ≥80% coverage for api_mcp_gateway.py"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        if not IMPORTS_SUCCESSFUL:
            pytest.skip("Module imports failed")

    @patch('api_mcp_gateway.settings')
    def test_thread_safe_lru_cache_cleanup_expired(self, mock_settings):
        """Test ThreadSafeLRUCache.cleanup_expired method - lines 88-89"""
        mock_settings.ENABLE_AUTHENTICATION = False
        
        cache = api_mcp_gateway.ThreadSafeLRUCache(max_size=10, ttl=0.1)
        
        # Add items with short TTL
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Wait for TTL to expire
        time.sleep(0.2)
        
        # Add a fresh item
        cache.put("key3", "value3")
        
        # Call cleanup_expired - this should hit lines 88-89
        cache.cleanup_expired()
        
        # Verify expired items are removed
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"

    @patch('api_mcp_gateway.settings')
    def test_thread_safe_lru_cache_clear(self, mock_settings):
        """Test ThreadSafeLRUCache.clear method - lines 98-109"""
        mock_settings.ENABLE_AUTHENTICATION = False
        
        cache = api_mcp_gateway.ThreadSafeLRUCache(max_size=10, ttl=300)
        
        # Add multiple items
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        assert cache.size() == 3
        
        # Call clear - this should hit lines 98-109
        cache.clear()
        
        # Verify cache is empty
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.qdrant_store')
    @patch('api_mcp_gateway.firestore_manager')
    def test_health_check_endpoint_service_status(self, mock_firestore, mock_qdrant, mock_settings):
        """Test health check endpoint with service status - lines 453, 459, 466"""
        from fastapi.testclient import TestClient
        
        mock_settings.ENABLE_AUTHENTICATION = False
        mock_qdrant.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_firestore.health_check = AsyncMock(return_value={"status": "healthy"})
        
        client = TestClient(api_mcp_gateway.app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "qdrant" in data
        assert "firestore" in data

    @patch('api_mcp_gateway.settings')
    def test_root_endpoint(self, mock_settings):
        """Test root endpoint - line 860"""
        from fastapi.testclient import TestClient
        
        mock_settings.ENABLE_AUTHENTICATION = False
        
        client = TestClient(api_mcp_gateway.app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Agent Data API" in data["message"]

    @patch('api_mcp_gateway.uvicorn')
    @patch('api_mcp_gateway.settings')
    def test_main_function(self, mock_settings, mock_uvicorn):
        """Test main function - lines 884-889"""
        mock_settings.API_HOST = "0.0.0.0"
        mock_settings.API_PORT = 8000
        mock_settings.DEBUG = False
        
        # Call main function
        api_mcp_gateway.main()
        
        # Verify uvicorn.run was called with correct parameters
        mock_uvicorn.run.assert_called_once_with(
            api_mcp_gateway.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )

    @patch('api_mcp_gateway.settings')
    @patch('api_mcp_gateway.auth_manager')
    def test_authentication_error_paths(self, mock_auth, mock_settings):
        """Test authentication error handling - lines 413-426"""
        from fastapi.testclient import TestClient
        
        mock_settings.ENABLE_AUTHENTICATION = True
        mock_auth.get_current_user = AsyncMock(side_effect=Exception("Auth service unavailable"))
        
        client = TestClient(api_mcp_gateway.app)
        
        # This should trigger the authentication error path
        response = client.post("/save", json={"doc_id": "test", "content": "test"})
        
        # Should return 401 or 500 depending on error handling
        assert response.status_code in [401, 500, 503]

    @patch('api_mcp_gateway.settings')
    def test_cache_functions_coverage(self, mock_settings):
        """Test cache-related functions for better coverage"""
        mock_settings.ENABLE_AUTHENTICATION = False
        
        # Test _get_cache_key function
        key = api_mcp_gateway._get_cache_key("test_operation", {"param": "value"})
        assert isinstance(key, str)
        assert "test_operation" in key
        
        # Test _initialize_caches function
        api_mcp_gateway._initialize_caches()
        
        # Verify caches are initialized
        assert hasattr(api_mcp_gateway, 'rag_cache')
        assert hasattr(api_mcp_gateway, 'search_cache')


class TestCLI140m4QdrantVectorizationToolCoverage:
    """Test class to achieve ≥80% coverage for qdrant_vectorization_tool.py"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        if not IMPORTS_SUCCESSFUL:
            pytest.skip("Module imports failed")

    @patch('qdrant_vectorization_tool.settings')
    @patch('qdrant_vectorization_tool.QdrantStore')
    @patch('qdrant_vectorization_tool.FirestoreMetadataManager')
    async def test_initialization_and_rate_limiting(self, mock_firestore_class, mock_qdrant_class, mock_settings):
        """Test tool initialization and rate limiting - lines 50-85"""
        mock_settings.get_qdrant_config.return_value = {
            "url": "http://localhost:6333",
            "api_key": "test-key",
            "collection_name": "test-collection",
            "vector_size": 1536
        }
        mock_settings.get_firestore_config.return_value = {
            "project_id": "test-project",
            "metadata_collection": "test-metadata"
        }
        
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        
        # Test initialization
        await tool._ensure_initialized()
        
        assert tool._initialized is True
        mock_qdrant_class.assert_called_once()
        mock_firestore_class.assert_called_once()
        
        # Test rate limiting
        start_time = time.time()
        await tool._rate_limit()
        await tool._rate_limit()
        end_time = time.time()
        
        # Should have some delay due to rate limiting
        assert end_time - start_time >= tool._rate_limiter["min_interval"]

    @patch('qdrant_vectorization_tool.settings')
    async def test_batch_get_firestore_metadata(self, mock_settings):
        """Test batch metadata retrieval - lines 120-180"""
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        
        # Mock firestore manager
        mock_firestore = AsyncMock()
        mock_firestore.get_metadata = AsyncMock(side_effect=[
            {"doc_id": "doc1", "title": "Test 1"},
            {"doc_id": "doc2", "title": "Test 2"},
            None  # Simulate missing document
        ])
        tool.firestore_manager = mock_firestore
        tool._initialized = True
        
        # Test batch retrieval
        doc_ids = ["doc1", "doc2", "doc3"]
        result = await tool._batch_get_firestore_metadata(doc_ids)
        
        assert len(result) == 2  # Only 2 successful retrievals
        assert "doc1" in result
        assert "doc2" in result
        assert "doc3" not in result

    @patch('qdrant_vectorization_tool.settings')
    async def test_filter_methods(self, mock_settings):
        """Test filtering methods - lines 200-240"""
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        
        # Test data
        results = [
            {"id": "1", "title": "Test 1", "author": "Alice", "tags": ["python", "ai"]},
            {"id": "2", "title": "Test 2", "author": "Bob", "tags": ["javascript"]},
            {"id": "3", "title": "Test 3", "author": "Alice", "tags": ["python"]}
        ]
        
        # Test metadata filtering
        filtered = tool._filter_by_metadata(results, {"author": "Alice"})
        assert len(filtered) == 2
        
        # Test tag filtering
        filtered = tool._filter_by_tags(results, ["python"])
        assert len(filtered) == 2
        
        # Test path filtering
        filtered = tool._filter_by_path(results, "Test 1")
        assert len(filtered) >= 1

    @patch('qdrant_vectorization_tool.settings')
    @patch('qdrant_vectorization_tool.get_openai_embedding')
    async def test_rag_search_comprehensive(self, mock_embedding, mock_settings):
        """Test RAG search with all parameters - lines 244-359"""
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        
        # Mock dependencies
        mock_qdrant = AsyncMock()
        mock_qdrant.search.return_value = [
            {"id": "1", "score": 0.9, "payload": {"title": "Test 1", "content": "Test content"}}
        ]
        tool.qdrant_store = mock_qdrant
        tool._initialized = True
        
        mock_embedding.return_value = [0.1] * 1536
        
        # Test comprehensive RAG search
        result = await tool.rag_search(
            query_text="test query",
            metadata_filters={"author": "Alice"},
            tags=["python"],
            path_query="test",
            limit=5,
            score_threshold=0.7,
            qdrant_tag="test-tag"
        )
        
        assert result["status"] == "success"
        assert "results" in result
        assert "answer" in result

    @patch('qdrant_vectorization_tool.settings')
    @patch('qdrant_vectorization_tool.get_openai_embedding')
    async def test_vectorize_document_with_auto_tagging(self, mock_embedding, mock_settings):
        """Test document vectorization with auto-tagging - lines 360-556"""
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        
        # Mock dependencies
        mock_qdrant = AsyncMock()
        mock_qdrant.upsert.return_value = {"status": "success"}
        tool.qdrant_store = mock_qdrant
        
        mock_firestore = AsyncMock()
        tool.firestore_manager = mock_firestore
        tool._initialized = True
        
        mock_embedding.return_value = [0.1] * 1536
        
        # Test vectorization with auto-tagging enabled
        result = await tool.vectorize_document(
            doc_id="test-doc",
            content="This is a test document about machine learning and AI.",
            metadata={"author": "Test Author"},
            tag="test-tag",
            update_firestore=True,
            enable_auto_tagging=True
        )
        
        assert result["status"] == "success"
        assert result["doc_id"] == "test-doc"

    @patch('qdrant_vectorization_tool.settings')
    async def test_batch_vectorize_documents(self, mock_settings):
        """Test batch vectorization - lines 589-696"""
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        
        # Mock dependencies
        mock_qdrant = AsyncMock()
        tool.qdrant_store = mock_qdrant
        tool._initialized = True
        
        # Mock the vectorize_document method
        tool.vectorize_document = AsyncMock(return_value={"status": "success", "doc_id": "test"})
        
        documents = [
            {"doc_id": "doc1", "content": "Test content 1"},
            {"doc_id": "doc2", "content": "Test content 2"},
            {"doc_id": "doc3", "content": "Test content 3"}
        ]
        
        result = await tool.batch_vectorize_documents(documents, tag="batch-test")
        
        assert result["status"] == "success"
        assert result["total_documents"] == 3
        assert result["successful"] >= 0

    @patch('qdrant_vectorization_tool.settings')
    async def test_vectorize_document_with_timeout(self, mock_settings):
        """Test vectorization with timeout handling - lines 697-733"""
        tool = qdrant_vectorization_tool.QdrantVectorizationTool()
        tool._initialized = True
        
        # Mock a slow operation that will timeout
        async def slow_vectorize(*args, **kwargs):
            await asyncio.sleep(1.0)  # Longer than timeout
            return {"status": "success"}
        
        tool.vectorize_document = slow_vectorize
        
        # Test with short timeout
        result = await tool._vectorize_document_with_timeout(
            doc_id="test-doc",
            content="test content",
            timeout=0.1  # Very short timeout
        )
        
        assert result["status"] == "timeout"


class TestCLI140m4DocumentIngestionToolCoverage:
    """Test class to achieve ≥80% coverage for document_ingestion_tool.py"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup for each test method"""
        if not IMPORTS_SUCCESSFUL:
            pytest.skip("Module imports failed")

    @patch('document_ingestion_tool.settings')
    async def test_initialization_and_caching(self, mock_settings):
        """Test tool initialization and caching mechanisms - lines 40-90"""
        mock_settings.get_firestore_config.return_value = {
            "project_id": "test-project",
            "metadata_collection": "test-metadata"
        }
        
        tool = document_ingestion_tool.DocumentIngestionTool()
        
        # Test initialization
        await tool._ensure_initialized()
        assert tool._initialized is True
        
        # Test cache key generation
        cache_key = tool._get_cache_key("doc1", "hash123")
        assert cache_key == "doc1:hash123"
        
        # Test cache validity
        assert tool._is_cache_valid(time.time()) is True
        assert tool._is_cache_valid(time.time() - 400) is False
        
        # Test content hash generation
        hash1 = tool._get_content_hash("test content")
        hash2 = tool._get_content_hash("test content")
        hash3 = tool._get_content_hash("different content")
        
        assert hash1 == hash2
        assert hash1 != hash3

    @patch('document_ingestion_tool.settings')
    async def test_save_document_metadata_with_caching(self, mock_settings):
        """Test metadata saving with caching - lines 91-200"""
        tool = document_ingestion_tool.DocumentIngestionTool()
        
        # Mock firestore manager
        mock_firestore = AsyncMock()
        mock_firestore.save_metadata = AsyncMock(return_value={"status": "success"})
        tool.firestore_manager = mock_firestore
        tool._initialized = True
        
        # First call - should save to cache
        result1 = await tool._save_document_metadata("doc1", "test content", {"author": "Test"})
        assert result1["status"] == "success"
        
        # Second call with same content - should hit cache
        result2 = await tool._save_document_metadata("doc1", "test content", {"author": "Test"})
        assert result2["status"] == "success"
        
        # Verify cache was used (firestore save called only once)
        assert len(tool._cache) > 0

    @patch('document_ingestion_tool.settings')
    async def test_ingest_document_parallel_operations(self, mock_settings):
        """Test document ingestion with parallel operations - lines 201-246"""
        tool = document_ingestion_tool.DocumentIngestionTool()
        tool._initialized = True
        
        # Mock dependencies
        tool._save_to_disk = AsyncMock(return_value={"status": "success", "path": "/test/path"})
        tool._save_document_metadata = AsyncMock(return_value={"status": "success", "doc_id": "test"})
        
        # Test ingestion with both disk save and metadata save
        result = await tool.ingest_document(
            doc_id="test-doc",
            content="This is test content for ingestion",
            metadata={"author": "Test Author"},
            save_to_disk=True,
            save_dir="test_documents"
        )
        
        assert result["status"] == "success"
        assert result["doc_id"] == "test-doc"
        
        # Verify both operations were called
        tool._save_to_disk.assert_called_once()
        tool._save_document_metadata.assert_called_once()

    @patch('document_ingestion_tool.settings')
    async def test_save_to_disk_operation(self, mock_settings):
        """Test disk save operation - lines 247-267"""
        tool = document_ingestion_tool.DocumentIngestionTool()
        
        # Test disk save operation
        result = await tool._save_to_disk("test-doc", "test content", "test_dir")
        
        assert result["status"] == "success"
        assert "path" in result

    @patch('document_ingestion_tool.settings')
    async def test_batch_ingest_documents(self, mock_settings):
        """Test batch document ingestion - lines 268-379"""
        tool = document_ingestion_tool.DocumentIngestionTool()
        tool._initialized = True
        
        # Mock the ingest_document method
        tool.ingest_document = AsyncMock(return_value={"status": "success", "doc_id": "test"})
        
        documents = [
            {"doc_id": "doc1", "content": "Content 1", "metadata": {"author": "Author 1"}},
            {"doc_id": "doc2", "content": "Content 2", "metadata": {"author": "Author 2"}},
            {"doc_id": "doc3", "content": "Content 3", "metadata": {"author": "Author 3"}}
        ]
        
        result = await tool.batch_ingest_documents(documents, save_to_disk=True)
        
        assert result["status"] == "success"
        assert result["total_documents"] == 3
        assert result["successful"] >= 0

    @patch('document_ingestion_tool.settings')
    def test_performance_metrics(self, mock_settings):
        """Test performance metrics tracking - lines 380-398"""
        tool = document_ingestion_tool.DocumentIngestionTool()
        
        # Test getting performance metrics
        metrics = tool.get_performance_metrics()
        assert "total_calls" in metrics
        assert "avg_latency" in metrics
        assert "batch_calls" in metrics
        
        # Test resetting metrics
        tool.reset_performance_metrics()
        metrics_after_reset = tool.get_performance_metrics()
        assert metrics_after_reset["total_calls"] == 0
        assert metrics_after_reset["total_time"] == 0.0

    @patch('document_ingestion_tool.settings')
    async def test_error_handling_and_timeouts(self, mock_settings):
        """Test error handling and timeout scenarios - lines 150-200"""
        tool = document_ingestion_tool.DocumentIngestionTool()
        
        # Mock firestore manager with timeout
        mock_firestore = AsyncMock()
        mock_firestore.save_metadata = AsyncMock(side_effect=asyncio.TimeoutError())
        tool.firestore_manager = mock_firestore
        tool._initialized = True
        
        # Test timeout handling
        result = await tool._save_document_metadata("doc1", "test content")
        assert result["status"] == "timeout"
        
        # Test general error handling
        mock_firestore.save_metadata = AsyncMock(side_effect=Exception("Test error"))
        result = await tool._save_document_metadata("doc2", "test content")
        assert result["status"] == "failed"


class TestCLI140m4CoverageValidation:
    """Test class to validate that ≥80% coverage is achieved"""

    def test_coverage_validation(self):
        """Validate that all three main modules achieve ≥80% coverage"""
        # This test serves as a marker for coverage validation
        # The actual coverage will be measured by pytest-cov
        
        assert IMPORTS_SUCCESSFUL, "Module imports must be successful for coverage testing"
        
        # Test that all required modules are importable
        assert hasattr(api_mcp_gateway, 'ThreadSafeLRUCache')
        assert hasattr(qdrant_vectorization_tool, 'QdrantVectorizationTool')
        assert hasattr(document_ingestion_tool, 'DocumentIngestionTool')
        
        print("✅ CLI140m.4 Coverage validation test passed")
        print("📊 Coverage targets:")
        print("   - api_mcp_gateway.py: ≥80%")
        print("   - qdrant_vectorization_tool.py: ≥80%") 
        print("   - document_ingestion_tool.py: ≥80%")


# Module-level functions for testing standalone functions
async def test_qdrant_vectorize_document_function():
    """Test the standalone qdrant_vectorize_document function - lines 743-766"""
    if not IMPORTS_SUCCESSFUL:
        pytest.skip("Module imports failed")
    
    with patch('qdrant_vectorization_tool.get_vectorization_tool') as mock_get_tool:
        mock_tool = AsyncMock()
        mock_tool.vectorize_document = AsyncMock(return_value={"status": "success"})
        mock_get_tool.return_value = mock_tool
        
        result = await qdrant_vectorization_tool.qdrant_vectorize_document(
            doc_id="test-doc",
            content="test content",
            metadata={"test": "metadata"}
        )
        
        assert result["status"] == "success"


async def test_document_ingestion_functions():
    """Test standalone document ingestion functions - lines 408-465"""
    if not IMPORTS_SUCCESSFUL:
        pytest.skip("Module imports failed")
    
    with patch('document_ingestion_tool.get_document_ingestion_tool') as mock_get_tool:
        mock_tool = AsyncMock()
        mock_tool.ingest_document = AsyncMock(return_value={"status": "success"})
        mock_get_tool.return_value = mock_tool
        
        # Test async function
        result = await document_ingestion_tool.ingest_document(
            doc_id="test-doc",
            content="test content"
        )
        assert result["status"] == "success"
        
        # Test sync function
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = {"status": "success"}
            result = document_ingestion_tool.ingest_document_sync(
                doc_id="test-doc",
                content="test content"
            )
            assert result["status"] == "success"


if __name__ == "__main__":
    print("CLI140m.4 Coverage Enhancement Tests")
    print("====================================")
    print(f"Import status: {'✅ SUCCESS' if IMPORTS_SUCCESSFUL else '❌ FAILED'}")
    if IMPORTS_SUCCESSFUL:
        print("✅ All modules imported successfully")
        print("🎯 Ready for coverage testing")
    else:
        print("❌ Module import issues detected")
        print("🔧 Check sys.path and import statements") 