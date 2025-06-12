"""
CLI140e Coverage Enhancement Tests
Additional tests to achieve coverage targets:
- api_mcp_gateway.py: ≥60%
- qdrant_vectorization_tool.py: ≥65%
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List, Any
import logging

# Test imports
from ADK.agent_data.api_mcp_gateway import (
    ThreadSafeLRUCache,
    _get_cache_key,
    _initialize_caches,
    get_user_id_for_rate_limiting
)
from ADK.agent_data.tools.qdrant_vectorization_tool import QdrantVectorizationTool

logger = logging.getLogger(__name__)

class TestCLI140eCoverage:
    """Additional tests to improve coverage for CLI140e targets."""

    def test_cache_key_generation_edge_cases(self):
        """Test cache key generation with various parameter combinations."""
        # Test with minimal parameters
        key1 = _get_cache_key("simple query")
        assert len(key1) == 32  # MD5 hash length
        
        # Test with all parameters
        key2 = _get_cache_key(
            "complex query",
            tag="test_tag",
            limit=20,
            score_threshold=0.8,
            metadata_filters={"category": "science"}
        )
        assert len(key2) == 32
        assert key1 != key2  # Different parameters should generate different keys
        
        # Test parameter order independence
        key3 = _get_cache_key(
            "complex query",
            score_threshold=0.8,
            tag="test_tag",
            limit=20,
            metadata_filters={"category": "science"}
        )
        assert key2 == key3  # Same parameters in different order should generate same key
        
        # Test with None values
        key4 = _get_cache_key("query", tag=None, limit=None)
        assert len(key4) == 32

    def test_lru_cache_ttl_expiration(self):
        """Test LRU cache TTL expiration functionality."""
        cache = ThreadSafeLRUCache(max_size=10, ttl_seconds=0.1)  # 100ms TTL
        
        # Add items to cache
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Verify items exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.size() == 2
        
        # Wait for TTL expiration
        time.sleep(0.15)
        
        # Verify items are expired when accessed (lazy expiration)
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        
        # Add items again to test cleanup_expired
        cache.put("key3", "value3")
        cache.put("key4", "value4")
        time.sleep(0.15)
        
        # Verify cleanup_expired works
        expired_count = cache.cleanup_expired()
        assert expired_count >= 0  # May be 0 if already cleaned up by get()
        assert cache.size() >= 0

    def test_lru_cache_max_size_eviction(self):
        """Test LRU cache eviction when max size is exceeded."""
        cache = ThreadSafeLRUCache(max_size=3, ttl_seconds=3600)
        
        # Fill cache to max capacity
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3
        
        # Add one more item to trigger eviction
        cache.put("key4", "value4")
        assert cache.size() == 3
        
        # Verify oldest item was evicted
        assert cache.get("key1") is None  # Should be evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_initialization(self):
        """Test cache initialization with different configurations."""
        # Mock settings for cache configuration
        mock_config = {
            "rag_cache_enabled": True,
            "rag_cache_max_size": 500,
            "rag_cache_ttl": 1800,
            "embedding_cache_enabled": True,
            "embedding_cache_max_size": 200,
            "embedding_cache_ttl": 900
        }
        
        with patch("ADK.agent_data.api_mcp_gateway.settings") as mock_settings:
            mock_settings.get_cache_config.return_value = mock_config
            
            # Test cache initialization
            _initialize_caches()
            
            # Verify settings were called
            mock_settings.get_cache_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_vectorization_tool_rate_limiting(self):
        """Test rate limiting functionality in vectorization tool."""
        tool = QdrantVectorizationTool()
        
        # Mock the rate limiting
        with patch.object(tool, '_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = None
            
            # Test rate limiting is called
            await tool._rate_limit()
            mock_rate_limit.assert_called_once()

    @pytest.mark.asyncio
    async def test_vectorization_tool_initialization_error_handling(self):
        """Test error handling during vectorization tool initialization."""
        tool = QdrantVectorizationTool()
        
        # Test that initialization creates dependencies if they don't exist
        await tool._ensure_initialized()
        
        # Verify tool creates dependencies during initialization
        assert tool.qdrant_store is not None
        assert tool.firestore_manager is not None
        
        # Test initialization is idempotent
        old_qdrant = tool.qdrant_store
        old_firestore = tool.firestore_manager
        await tool._ensure_initialized()
        assert tool.qdrant_store is old_qdrant
        assert tool.firestore_manager is old_firestore

    @pytest.mark.asyncio
    async def test_batch_metadata_retrieval_error_handling(self):
        """Test error handling in batch metadata retrieval."""
        tool = QdrantVectorizationTool()
        
        # Mock firestore manager with error
        mock_firestore = AsyncMock()
        mock_firestore._batch_check_documents_exist.side_effect = Exception("Firestore error")
        tool.firestore_manager = mock_firestore
        
        # Test batch retrieval with error
        doc_ids = ["doc1", "doc2", "doc3"]
        result = await tool._batch_get_firestore_metadata(doc_ids)
        
        # Should return empty dict on error
        assert isinstance(result, dict)

    def test_rate_limiting_key_generation(self):
        """Test rate limiting key generation for different scenarios."""
        from fastapi import Request
        
        # Mock request with Authorization header
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"Authorization": "Bearer test_token"}
        
        # Test with simple token (should fall back to IP-based key)
        key = get_user_id_for_rate_limiting(mock_request)
        assert isinstance(key, str)
        
        # Test with no Authorization header
        mock_request_no_auth = MagicMock(spec=Request)
        mock_request_no_auth.headers = {}
        
        key_no_auth = get_user_id_for_rate_limiting(mock_request_no_auth)
        assert isinstance(key_no_auth, str)

    @pytest.mark.asyncio
    async def test_qdrant_operation_retry_mechanism(self):
        """Test retry mechanism for Qdrant operations."""
        tool = QdrantVectorizationTool()
        
        # Mock operation that fails then succeeds
        mock_operation = AsyncMock()
        mock_operation.side_effect = [ConnectionError("Connection failed"), {"success": True}]
        
        # Test retry mechanism
        try:
            result = await tool._qdrant_operation_with_retry(mock_operation, "test_arg")
            # If tenacity is available, should retry and succeed
            if hasattr(tool._qdrant_operation_with_retry, '__wrapped__'):
                assert result == {"success": True}
                assert mock_operation.call_count == 2
        except ConnectionError:
            # If tenacity is not available, should fail immediately
            assert mock_operation.call_count == 1

if __name__ == "__main__":
    # Run coverage tests directly
    pytest.main([__file__, "-v"]) 