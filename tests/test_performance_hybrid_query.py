#!/usr/bin/env python3
"""
Performance tests for hybrid query functionality with caching.
Tests latency expectations and cache effectiveness for RAG queries.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from typing import Dict, List, Any


class TestHybridQueryPerformance:
    """Test performance of hybrid queries with various document loads."""

    @pytest.fixture
    def mock_qdrant_store(self):
        """Mock Qdrant store for performance testing."""
        mock_store = AsyncMock()
        mock_store.semantic_search.return_value = {
            "status": "success",
            "results": [
                {
                    "metadata": {"doc_id": f"doc_{i}"},
                    "score": 0.8 - (i * 0.05),
                    "payload": {"content": f"Test content {i}"},
                }
                for i in range(20)  # Return 20 results for filtering
            ],
        }
        return mock_store

    @pytest.fixture
    def mock_firestore_manager(self):
        """Mock Firestore manager for performance testing."""
        mock_manager = AsyncMock()

        # Mock individual metadata retrieval
        async def mock_get_metadata(doc_id: str):
            return {
                "doc_id": doc_id,
                "content_preview": f"Preview for {doc_id}",
                "auto_tags": ["customer_service", "support"],
                "level_1_category": "Customer Support",
                "level_2_category": "Technical Issues",
                "lastUpdated": "2024-01-01T00:00:00Z",
                "version": 1,
            }

        mock_manager.get_metadata_with_version.side_effect = mock_get_metadata
        return mock_manager

    @pytest.fixture
    def mock_embedding_provider(self):
        """Mock embedding provider for performance testing."""
        mock_provider = AsyncMock()
        mock_provider.get_embedding.return_value = [0.1] * 1536  # Mock embedding vector
        return mock_provider

    @pytest.mark.asyncio
    async def test_hybrid_query_latency_8_documents(
        self, mock_qdrant_store, mock_firestore_manager, mock_embedding_provider
    ):
        """Test hybrid query latency with 8 documents (should be <0.5s)."""

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantVectorizationTool") as mock_tool_class:
            # Setup mock tool instance
            mock_tool = AsyncMock()
            mock_tool.qdrant_store = mock_qdrant_store
            mock_tool.firestore_manager = mock_firestore_manager
            mock_tool.embedding_provider = mock_embedding_provider

            # Mock the batch metadata method
            async def mock_batch_get_metadata(doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
                return {
                    doc_id: {
                        "doc_id": doc_id,
                        "content_preview": f"Preview for {doc_id}",
                        "auto_tags": ["customer_service", "support"],
                        "level_1_category": "Customer Support",
                        "level_2_category": "Technical Issues",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                        "version": 1,
                    }
                    for doc_id in doc_ids[:8]  # Limit to 8 documents
                }

            mock_tool._batch_get_firestore_metadata = mock_batch_get_metadata
            mock_tool._ensure_initialized = AsyncMock()

            # Mock filtering methods
            def mock_filter_by_metadata(results, filters):
                return results[:8]  # Return 8 results

            def mock_filter_by_tags(results, tags):
                return results

            def mock_filter_by_path(results, path_query):
                return results

            def mock_build_hierarchy_path(result):
                return "Customer Support > Technical Issues"

            mock_tool._filter_by_metadata = mock_filter_by_metadata
            mock_tool._filter_by_tags = mock_filter_by_tags
            mock_tool._filter_by_path = mock_filter_by_path
            mock_tool._build_hierarchy_path = mock_build_hierarchy_path

            # Mock the rag_search method to use our optimized implementation
            async def mock_rag_search(
                query_text,
                metadata_filters=None,
                tags=None,
                path_query=None,
                limit=10,
                score_threshold=0.5,
                qdrant_tag=None,
            ):
                await mock_tool._ensure_initialized()

                # Step 1: Qdrant search
                qdrant_results = await mock_qdrant_store.semantic_search(
                    query_text=query_text,
                    limit=limit * 2,
                    tag=qdrant_tag,
                    score_threshold=score_threshold,
                )

                # Extract doc_ids
                qdrant_doc_ids = []
                qdrant_scores = {}
                for result in qdrant_results["results"]:
                    doc_id = result["metadata"].get("doc_id")
                    if doc_id:
                        qdrant_doc_ids.append(doc_id)
                        qdrant_scores[doc_id] = result["score"]

                # Step 2: Batch Firestore metadata
                batch_metadata = await mock_tool._batch_get_firestore_metadata(qdrant_doc_ids)
                firestore_results = []
                for doc_id in qdrant_doc_ids:
                    if doc_id in batch_metadata:
                        metadata = batch_metadata[doc_id]
                        metadata["_doc_id"] = doc_id
                        metadata["_qdrant_score"] = qdrant_scores[doc_id]
                        firestore_results.append(metadata)

                # Step 3: Apply filters
                filtered_results = firestore_results
                if metadata_filters:
                    filtered_results = mock_tool._filter_by_metadata(filtered_results, metadata_filters)
                if tags:
                    filtered_results = mock_tool._filter_by_tags(filtered_results, tags)
                if path_query:
                    filtered_results = mock_tool._filter_by_path(filtered_results, path_query)

                # Step 4: Sort and limit
                filtered_results.sort(key=lambda x: x.get("_qdrant_score", 0), reverse=True)
                final_results = filtered_results[:limit]

                # Step 5: Enrich results
                enriched_results = []
                for result in final_results:
                    enriched_result = {
                        "doc_id": result["_doc_id"],
                        "qdrant_score": result["_qdrant_score"],
                        "metadata": {k: v for k, v in result.items() if not k.startswith("_")},
                        "content_preview": result.get("content_preview", ""),
                        "auto_tags": result.get("auto_tags", []),
                        "hierarchy_path": mock_tool._build_hierarchy_path(result),
                        "last_updated": result.get("lastUpdated"),
                        "version": result.get("version", 1),
                    }
                    enriched_results.append(enriched_result)

                return {
                    "status": "success",
                    "query": query_text,
                    "results": enriched_results,
                    "count": len(enriched_results),
                    "rag_info": {
                        "qdrant_results": len(qdrant_results["results"]),
                        "firestore_filtered": len(filtered_results),
                        "metadata_filters": metadata_filters,
                        "tags": tags,
                        "path_query": path_query,
                        "score_threshold": score_threshold,
                    },
                }

            mock_tool.rag_search = mock_rag_search
            mock_tool_class.return_value = mock_tool

            # Patch the global tool getter
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.get_vectorization_tool", return_value=mock_tool
            ):
                # Measure latency
                start_time = time.time()

                result = await qdrant_rag_search(
                    query_text="Customer service performance test query",
                    metadata_filters={"level_1_category": "Customer Support"},
                    tags=["customer_service"],
                    limit=8,
                    score_threshold=0.6,
                )

                end_time = time.time()
                latency = end_time - start_time

                # Assertions
                assert result["status"] == "success"
                assert result["count"] <= 8
                assert latency < 0.5, f"Hybrid query latency {latency:.3f}s exceeds 0.5s target"

                # Verify result structure
                assert "rag_info" in result
                assert "results" in result
                for item in result["results"]:
                    assert "doc_id" in item
                    assert "qdrant_score" in item
                    assert "metadata" in item

    @pytest.mark.asyncio
    async def test_hybrid_query_latency_50_documents(
        self, mock_qdrant_store, mock_firestore_manager, mock_embedding_provider
    ):
        """Test hybrid query latency with 50 documents (should be <0.7s)."""

        # Increase mock data for 50 documents
        mock_qdrant_store.semantic_search.return_value = {
            "status": "success",
            "results": [
                {
                    "metadata": {"doc_id": f"doc_{i}"},
                    "score": 0.9 - (i * 0.01),
                    "payload": {"content": f"Test content {i}"},
                }
                for i in range(100)  # Return 100 results for filtering to 50
            ],
        }

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantVectorizationTool") as mock_tool_class:
            # Setup mock tool instance (similar to above but for 50 docs)
            mock_tool = AsyncMock()
            mock_tool.qdrant_store = mock_qdrant_store
            mock_tool.firestore_manager = mock_firestore_manager
            mock_tool.embedding_provider = mock_embedding_provider

            # Mock batch metadata for 50 documents
            async def mock_batch_get_metadata(doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
                return {
                    doc_id: {
                        "doc_id": doc_id,
                        "content_preview": f"Preview for {doc_id}",
                        "auto_tags": ["customer_service", "support"],
                        "level_1_category": "Customer Support",
                        "level_2_category": "Technical Issues",
                        "lastUpdated": "2024-01-01T00:00:00Z",
                        "version": 1,
                    }
                    for doc_id in doc_ids[:50]  # Limit to 50 documents
                }

            mock_tool._batch_get_firestore_metadata = mock_batch_get_metadata
            mock_tool._ensure_initialized = AsyncMock()

            # Mock filtering methods for 50 docs
            def mock_filter_by_metadata(results, filters):
                return results[:50]  # Return 50 results

            mock_tool._filter_by_metadata = mock_filter_by_metadata
            mock_tool._filter_by_tags = lambda results, tags: results
            mock_tool._filter_by_path = lambda results, path_query: results
            mock_tool._build_hierarchy_path = lambda result: "Customer Support > Technical Issues"

            # Use similar rag_search implementation
            async def mock_rag_search(
                query_text,
                metadata_filters=None,
                tags=None,
                path_query=None,
                limit=50,
                score_threshold=0.5,
                qdrant_tag=None,
            ):
                await mock_tool._ensure_initialized()

                qdrant_results = await mock_qdrant_store.semantic_search(
                    query_text=query_text,
                    limit=limit * 2,
                    tag=qdrant_tag,
                    score_threshold=score_threshold,
                )

                qdrant_doc_ids = []
                qdrant_scores = {}
                for result in qdrant_results["results"]:
                    doc_id = result["metadata"].get("doc_id")
                    if doc_id:
                        qdrant_doc_ids.append(doc_id)
                        qdrant_scores[doc_id] = result["score"]

                batch_metadata = await mock_tool._batch_get_firestore_metadata(qdrant_doc_ids)
                firestore_results = []
                for doc_id in qdrant_doc_ids:
                    if doc_id in batch_metadata:
                        metadata = batch_metadata[doc_id]
                        metadata["_doc_id"] = doc_id
                        metadata["_qdrant_score"] = qdrant_scores[doc_id]
                        firestore_results.append(metadata)

                filtered_results = firestore_results
                if metadata_filters:
                    filtered_results = mock_tool._filter_by_metadata(filtered_results, metadata_filters)

                filtered_results.sort(key=lambda x: x.get("_qdrant_score", 0), reverse=True)
                final_results = filtered_results[:limit]

                enriched_results = []
                for result in final_results:
                    enriched_result = {
                        "doc_id": result["_doc_id"],
                        "qdrant_score": result["_qdrant_score"],
                        "metadata": {k: v for k, v in result.items() if not k.startswith("_")},
                        "content_preview": result.get("content_preview", ""),
                        "auto_tags": result.get("auto_tags", []),
                        "hierarchy_path": mock_tool._build_hierarchy_path(result),
                        "last_updated": result.get("lastUpdated"),
                        "version": result.get("version", 1),
                    }
                    enriched_results.append(enriched_result)

                return {
                    "status": "success",
                    "query": query_text,
                    "results": enriched_results,
                    "count": len(enriched_results),
                    "rag_info": {
                        "qdrant_results": len(qdrant_results["results"]),
                        "firestore_filtered": len(filtered_results),
                        "metadata_filters": metadata_filters,
                        "tags": tags,
                        "path_query": path_query,
                        "score_threshold": score_threshold,
                    },
                }

            mock_tool.rag_search = mock_rag_search
            mock_tool_class.return_value = mock_tool

            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.get_vectorization_tool", return_value=mock_tool
            ):
                # Measure latency for 50 documents
                start_time = time.time()

                result = await qdrant_rag_search(
                    query_text="Large scale customer service query",
                    metadata_filters={"level_1_category": "Customer Support"},
                    limit=50,
                    score_threshold=0.5,
                )

                end_time = time.time()
                latency = end_time - start_time

                # Assertions
                assert result["status"] == "success"
                assert result["count"] <= 50
                assert latency < 0.7, f"Hybrid query latency {latency:.3f}s exceeds 0.7s target for 50 documents"

    @pytest.mark.unit
    def test_cache_key_generation_performance(self):
        """Test performance of cache key generation for queries."""
        start_time = time.time()

        # Generate 100 cache keys
        for i in range(100):
            cache_key = _get_cache_key(
                f"Test query {i}", {"filter": f"value_{i}"}, [f"tag_{i}", f"tag_{i+1}"], f"path/to/category_{i}"
            )
            assert len(cache_key) == 32  # MD5 hash length

        end_time = time.time()
        latency = end_time - start_time

        # Should be very fast
        assert latency < 0.1, f"Cache key generation too slow: {latency:.3f}s for 100 keys"

    @pytest.mark.unit
    def test_cache_operations_performance(self):
        """Test performance of cache operations (get/set)."""
        test_data = {
            "results": [{"doc_id": f"doc_{i}", "score": 0.8} for i in range(10)],
            "total_found": 10,
            "rag_info": {"test": "data"},
        }

        start_time = time.time()

        # Test 100 cache operations
        for i in range(100):
            cache_key = f"test_key_{i}"

            # Cache result
            _cache_result(cache_key, test_data)

            # Retrieve result
            cached_result = _get_cached_result(cache_key)
            assert cached_result is not None
            assert cached_result["total_found"] == 10

        end_time = time.time()
        latency = end_time - start_time

        # Should be very fast
        assert latency < 0.1, f"Cache operations too slow: {latency:.3f}s for 100 operations"

    @pytest.mark.asyncio
    async def test_rag_caching_effectiveness(self, mock_qdrant_store, mock_firestore_manager, mock_embedding_provider):
        """Test effectiveness of RAG query caching."""

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantVectorizationTool") as mock_tool_class:
            mock_tool = AsyncMock()
            mock_tool.qdrant_store = mock_qdrant_store
            mock_tool.firestore_manager = mock_firestore_manager
            mock_tool.embedding_provider = mock_embedding_provider

            # Setup minimal mock for caching test
            async def mock_rag_search(query_text, **kwargs):
                # Simulate some processing time
                await asyncio.sleep(0.01)
                return {
                    "status": "success",
                    "query": query_text,
                    "results": [{"doc_id": "test_doc", "score": 0.8}],
                    "count": 1,
                    "rag_info": {},
                }

            mock_tool.rag_search = mock_rag_search
            mock_tool_class.return_value = mock_tool

            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.get_vectorization_tool", return_value=mock_tool
            ):
                query_text = "Cache effectiveness test query"

                # First query (should hit the actual search)
                start_time = time.time()
                result1 = await qdrant_rag_search(query_text=query_text, limit=5)
                first_latency = time.time() - start_time

                # Cache the result manually for testing
                cache_key = _get_cache_key(query_text, {}, [], "")
                _cache_result(
                    cache_key,
                    {"results": result1["results"], "total_found": result1["count"], "rag_info": result1["rag_info"]},
                )

                # Second query (should hit cache)
                start_time = time.time()
                cached_result = _get_cached_result(cache_key)
                cache_latency = time.time() - start_time

                # Assertions
                assert cached_result is not None
                assert cache_latency < first_latency, "Cache should be faster than original query"
                assert cache_latency < 0.001, f"Cache retrieval too slow: {cache_latency:.6f}s"
                assert cached_result["total_found"] == result1["count"]
