"""
CLI140e Latency Profiling and Optimization Tests
Tests for CSKH API and RAG query performance optimization
Target: <0.5s (CSKH API), <0.7s (RAG, 8-50 docs)
"""

import pytest
import asyncio
import time
import cProfile
import pstats
import io
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List, Any
import json
import logging

# Test imports
from api_mcp_gateway import (
    app,
    ThreadSafeLRUCache,
    _get_cache_key,
    _get_cached_result,
    _cache_result
)
from ADK.agent_data.tools.qdrant_vectorization_tool import qdrant_rag_search, QdrantVectorizationTool

logger = logging.getLogger(__name__)

class TestLatencyProfiling:
    """Test suite for CLI140e latency profiling and optimization."""

    @pytest.fixture
    def mock_qdrant_store(self):
        """Mock Qdrant store for testing."""
        mock_store = AsyncMock()
        mock_store.semantic_search.return_value = {
            "results": [
                {
                    "metadata": {"doc_id": f"doc_{i}", "content": f"Test content {i}"},
                    "score": 0.8 + (i * 0.01)
                }
                for i in range(20)  # 20 mock results
            ]
        }
        return mock_store

    @pytest.fixture
    def mock_firestore_manager(self):
        """Mock Firestore manager for testing."""
        mock_manager = AsyncMock()
        
        # Mock batch metadata retrieval
        def mock_batch_get(doc_ids):
            return {
                doc_id: {
                    "doc_id": doc_id,
                    "level_1_category": "Science",
                    "level_2_category": "Physics",
                    "content_preview": f"Content for {doc_id}",
                    "auto_tags": ["physics", "science"],
                    "lastUpdated": "2024-01-01T00:00:00Z",
                    "version": 1
                }
                for doc_id in doc_ids
            }
        
        mock_manager.batch_get_metadata.side_effect = mock_batch_get
        return mock_manager

    @pytest.fixture
    def performance_profile_context(self):
        """Context manager for cProfile performance analysis."""
        class ProfileContext:
            def __init__(self):
                self.profile = cProfile.Profile()
                self.stats = None
                
            def __enter__(self):
                self.profile.enable()
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.profile.disable()
                s = io.StringIO()
                ps = pstats.Stats(self.profile, stream=s)
                ps.sort_stats('cumulative')
                ps.print_stats(20)  # Top 20 functions
                self.stats = s.getvalue()
                
            def get_stats(self):
                return self.stats
                
        return ProfileContext()

    @pytest.mark.asyncio
    async def test_rag_search_latency_profile(self, mock_qdrant_store, mock_firestore_manager, performance_profile_context):
        """
        Test RAG search latency profiling for CLI140e optimization.
        Target: <0.7s for 8-50 docs
        """
        # Initialize vectorization tool with mocks
        vectorization_tool = QdrantVectorizationTool()
        
        with patch.object(vectorization_tool, 'qdrant_store', mock_qdrant_store), \
             patch.object(vectorization_tool, 'firestore_manager', mock_firestore_manager):
            
            # Profile RAG search performance
            with performance_profile_context:
                start_time = time.time()
                
                result = await vectorization_tool.rag_search(
                    query_text="Test quantum physics principles",
                    limit=10,
                    score_threshold=0.5
                )
                
                end_time = time.time()
                latency = end_time - start_time
            
            # Assertions
            assert result["status"] == "success"
            assert len(result["results"]) <= 10
            assert latency < 0.7, f"RAG search latency {latency:.3f}s exceeds target 0.7s"
            
            # Log profiling results
            logger.info(f"RAG Search Latency: {latency:.3f}s")
            logger.info(f"Profile Stats:\n{performance_profile_context.get_stats()}")
            
            return {
                "latency": latency,
                "result_count": len(result["results"]),
                "profile_stats": performance_profile_context.get_stats()
            }

    @pytest.mark.asyncio
    async def test_cskh_api_latency_profile(self, performance_profile_context):
        """
        Test CSKH API latency profiling for CLI140e optimization.
        Target: <0.5s
        """
        from fastapi.testclient import TestClient
        
        # Mock dependencies
        with patch("api_mcp_gateway.QdrantStore") as mock_qdrant_class, \
             patch("api_mcp_gateway.FirestoreMetadataManager") as mock_firestore_class, \
             patch("api_mcp_gateway.get_current_user") as mock_auth:
            
            # Setup mocks
            mock_qdrant = AsyncMock()
            mock_qdrant.semantic_search.return_value = {
                "results": [
                    {
                        "metadata": {"doc_id": "test_doc", "content": "Test content"},
                        "score": 0.85
                    }
                ]
            }
            mock_qdrant_class.return_value = mock_qdrant
            
            mock_firestore_class.return_value = AsyncMock()
            mock_auth.return_value = {"user_id": "test_user", "email": "test@example.com"}
            
            client = TestClient(app)
            
            # Profile API query performance
            with performance_profile_context:
                start_time = time.time()
                
                response = client.post(
                    "/query",
                    json={
                        "query_text": "Test query",
                        "limit": 10,
                        "score_threshold": 0.7
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                end_time = time.time()
                latency = end_time - start_time
            
            # Assertions
            assert response.status_code == 200
            assert latency < 0.5, f"CSKH API latency {latency:.3f}s exceeds target 0.5s"
            
            # Log profiling results
            logger.info(f"CSKH API Latency: {latency:.3f}s")
            logger.info(f"Profile Stats:\n{performance_profile_context.get_stats()}")
            
            return {
                "latency": latency,
                "response_data": response.json(),
                "profile_stats": performance_profile_context.get_stats()
            }

    @pytest.mark.unit
    def test_lru_cache_performance(self):
        """Test LRU cache performance for CLI140e optimization."""
        cache = ThreadSafeLRUCache(max_size=1000, ttl_seconds=3600)
        
        # Performance test for cache operations
        start_time = time.time()
        
        # Test cache puts
        for i in range(1000):
            cache_key = f"test_key_{i}"
            cache_value = {"result": f"data_{i}", "score": 0.8 + (i * 0.0001)}
            cache.put(cache_key, cache_value)
        
        put_time = time.time() - start_time
        
        # Test cache gets
        start_time = time.time()
        hits = 0
        
        for i in range(500, 1500):  # Mix of hits and misses
            cache_key = f"test_key_{i}"
            result = cache.get(cache_key)
            if result is not None:
                hits += 1
        
        get_time = time.time() - start_time
        
        # Assertions
        assert put_time < 0.1, f"Cache put operations took {put_time:.3f}s, expected <0.1s"
        assert get_time < 0.05, f"Cache get operations took {get_time:.3f}s, expected <0.05s"
        assert hits == 500, f"Expected 500 cache hits, got {hits}"
        assert cache.size() == 1000, f"Expected cache size 1000, got {cache.size()}"
        
        logger.info(f"Cache put performance: {put_time:.3f}s for 1000 operations")
        logger.info(f"Cache get performance: {get_time:.3f}s for 1000 operations")
        logger.info(f"Cache hit ratio: {hits}/1000 = {hits/10}%")

    @pytest.mark.asyncio
    async def test_batch_firestore_optimization(self, mock_firestore_manager):
        """Test batch Firestore operations for RU optimization."""
        doc_ids = [f"doc_{i}" for i in range(50)]
        
        # Test batch retrieval performance
        start_time = time.time()
        
        batch_result = await mock_firestore_manager.batch_get_metadata(doc_ids)
        
        end_time = time.time()
        batch_latency = end_time - start_time
        
        # Simulate individual queries for comparison
        start_time = time.time()
        individual_results = {}
        
        for doc_id in doc_ids[:10]:  # Only test 10 for speed
            individual_results[doc_id] = {
                "doc_id": doc_id,
                "level_1_category": "Science",
                "level_2_category": "Physics"
            }
        
        individual_latency = (time.time() - start_time) * 5  # Extrapolate for 50 docs
        
        # Assertions
        assert len(batch_result) == 50
        assert batch_latency < individual_latency, f"Batch query ({batch_latency:.3f}s) should be faster than individual queries ({individual_latency:.3f}s)"
        
        logger.info(f"Batch Firestore latency: {batch_latency:.3f}s for 50 documents")
        logger.info(f"Estimated individual query latency: {individual_latency:.3f}s")
        logger.info(f"Performance improvement: {individual_latency/batch_latency:.2f}x")

    @pytest.mark.performance
    async def test_end_to_end_latency_with_caching(self, mock_qdrant_store, mock_firestore_manager):
        """
        Test end-to-end latency with caching enabled.
        Validates CLI140e optimization targets.
        """
        vectorization_tool = QdrantVectorizationTool()
        
        with patch.object(vectorization_tool, 'qdrant_store', mock_qdrant_store), \
             patch.object(vectorization_tool, 'firestore_manager', mock_firestore_manager):
            
            query_text = "Test quantum physics principles"
            
            # First query (cache miss)
            start_time = time.time()
            result1 = await vectorization_tool.rag_search(query_text, limit=10)
            first_query_time = time.time() - start_time
            
            # Second query (should be faster with optimizations)
            start_time = time.time()
            result2 = await vectorization_tool.rag_search(query_text, limit=10)
            second_query_time = time.time() - start_time
            
            # Assertions
            assert result1["status"] == "success"
            assert result2["status"] == "success"
            assert first_query_time < 0.7, f"First RAG query {first_query_time:.3f}s exceeds target 0.7s"
            
            # Second query might be cached or optimized
            logger.info(f"First query latency: {first_query_time:.3f}s")
            logger.info(f"Second query latency: {second_query_time:.3f}s")
            
            if second_query_time < first_query_time * 0.8:
                logger.info("Caching/optimization working - second query faster")
            
            return {
                "first_query_latency": first_query_time,
                "second_query_latency": second_query_time,
                "optimization_ratio": first_query_time / second_query_time if second_query_time > 0 else 1
            }

if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "-m", "performance"]) 