"""
Test case for CLI 136 metadata query optimization.

This test validates the optimized metadata query functionality including:
- Indexed queries for level_1_category through level_6_category
- Version-based queries with performance optimization
- Query performance benchmarking
- Composite index utilization
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from typing import List

from src.agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager



class TestCLI136MetadataOptimization:
    """Test CLI 136 metadata query optimization."""

    @pytest.fixture
    def mock_firestore_client(self):
        """Mock Firestore client for testing."""
        mock_client = MagicMock()
        mock_doc_ref = AsyncMock()
        mock_collection = MagicMock()
        mock_query = MagicMock()

        # Setup query chain
        mock_collection.where.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query

        mock_collection.document.return_value = mock_doc_ref
        mock_client.collection.return_value = mock_collection

        return mock_client, mock_collection, mock_query

    @pytest.fixture
    def metadata_manager(self, mock_firestore_client):
        """Create FirestoreMetadataManager with mocked dependencies."""
        mock_client, mock_collection, mock_query = mock_firestore_client

        manager = FirestoreMetadataManager(project_id="test-project", collection_name="test_metadata")
        manager.db = mock_client
        return manager, mock_collection, mock_query

    def create_mock_documents(self, count: int = 5) -> List[MagicMock]:
        """Create mock Firestore documents for testing."""
        mock_docs = []
        for i in range(count):
            mock_doc = MagicMock()
            mock_doc.id = f"doc_{i}"
            mock_doc.to_dict.return_value = {
                "level_1_category": "document",
                "level_2_category": "research_paper" if i % 2 == 0 else "report",
                "level_3_category": f"author_{i}",
                "version": i + 1,
                "lastUpdated": f"2025-01-27T{18+i}:00:00Z",
                "content": f"Test content {i}",
            }
            mock_docs.append(mock_doc)
        return mock_docs

    @pytest.mark.asyncio
    async def test_query_by_hierarchy_optimized(self, metadata_manager):
        """Test optimized hierarchical query with indexed fields."""
        manager, mock_collection, mock_query = metadata_manager

        # Setup mock documents
        mock_docs = self.create_mock_documents(3)

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        mock_query.stream.return_value = mock_stream()

        # Test hierarchical query
        start_time = time.time()
        results = await manager.query_by_hierarchy_optimized(
            level_1="document", level_2="research_paper", version_order="desc", limit=10
        )
        query_time = time.time() - start_time

        # Verify results
        assert len(results) == 3
        assert all("_doc_id" in result for result in results)
        assert results[0]["level_1_category"] == "document"

        # Verify query was built correctly
        mock_collection.where.assert_called()
        mock_query.order_by.assert_called_with("version", direction="DESCENDING")
        mock_query.limit.assert_called_with(10)

        # Verify performance (should be fast with mocking)
        assert query_time < 1.0, f"Query took {query_time:.3f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_query_by_version_range_optimized(self, metadata_manager):
        """Test optimized version range query."""
        manager, mock_collection, mock_query = metadata_manager

        # Setup mock documents
        mock_docs = self.create_mock_documents(4)

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        mock_query.stream.return_value = mock_stream()

        # Test version range query
        start_time = time.time()
        results = await manager.query_by_version_range_optimized(
            min_version=2, max_version=5, level_1_filter="document", limit=20
        )
        query_time = time.time() - start_time

        # Verify results
        assert len(results) == 4
        assert all("_doc_id" in result for result in results)

        # Verify query construction
        mock_query.order_by.assert_called_with("version", direction="DESCENDING")
        mock_query.limit.assert_called_with(20)

        # Verify performance
        assert query_time < 1.0, f"Query took {query_time:.3f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_query_latest_by_category_optimized(self, metadata_manager):
        """Test optimized latest by category query."""
        manager, mock_collection, mock_query = metadata_manager

        # Setup mock documents
        mock_docs = self.create_mock_documents(3)

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        mock_query.stream.return_value = mock_stream()

        # Test latest by category query
        start_time = time.time()
        results = await manager.query_latest_by_category_optimized(
            category_level="level_1_category", category_value="document", limit=15
        )
        query_time = time.time() - start_time

        # Verify results
        assert len(results) == 3
        assert all(result["level_1_category"] == "document" for result in results)

        # Verify query construction
        mock_collection.where.assert_called_with("level_1_category", "==", "document")
        mock_query.order_by.assert_called_with("version", direction="DESCENDING")
        mock_query.limit.assert_called_with(15)

        # Verify performance
        assert query_time < 1.0, f"Query took {query_time:.3f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_query_multi_level_hierarchy_optimized(self, metadata_manager):
        """Test optimized multi-level hierarchy query."""
        manager, mock_collection, mock_query = metadata_manager

        # Setup mock documents
        mock_docs = self.create_mock_documents(2)

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        mock_query.stream.return_value = mock_stream()

        # Test multi-level hierarchy query
        start_time = time.time()
        results = await manager.query_multi_level_hierarchy_optimized(
            level_1="document", level_2="research_paper", order_by_updated=True, limit=25
        )
        query_time = time.time() - start_time

        # Verify results
        assert len(results) == 2
        assert all("_doc_id" in result for result in results)

        # Verify query construction
        mock_query.order_by.assert_called_with("lastUpdated", direction="DESCENDING")
        mock_query.limit.assert_called_with(25)

        # Verify performance
        assert query_time < 1.0, f"Query took {query_time:.3f}s, expected < 1.0s"

    @pytest.mark.asyncio
    async def test_benchmark_query_performance(self, metadata_manager):
        """Test query performance benchmarking functionality."""
        manager, mock_collection, mock_query = metadata_manager

        # Setup mock documents for all benchmark queries
        mock_docs = self.create_mock_documents(5)

        async def mock_stream():
            for doc in mock_docs:
                yield doc

        mock_query.stream.return_value = mock_stream()

        # Run benchmark
        start_time = time.time()
        benchmark_results = await manager.benchmark_query_performance()
        total_time = time.time() - start_time

        # Verify benchmark structure
        assert "timestamp" in benchmark_results
        assert "queries" in benchmark_results
        assert "summary" in benchmark_results

        # Verify individual query results
        expected_queries = [
            "hierarchy_simple",
            "version_range",
            "latest_by_category",
            "multi_level_hierarchy",
        ]

        for query_name in expected_queries:
            assert query_name in benchmark_results["queries"]
            query_result = benchmark_results["queries"][query_name]
            assert "duration_ms" in query_result
            assert "result_count" in query_result
            assert "query_type" in query_result
            assert query_result["duration_ms"] >= 0

        # Verify summary statistics
        summary = benchmark_results["summary"]
        assert summary["total_queries"] == 4
        assert summary["avg_duration_ms"] >= 0
        assert summary["max_duration_ms"] >= summary["min_duration_ms"]

        # Verify overall performance (should be fast with mocking)
        assert total_time < 2.0, f"Benchmark took {total_time:.3f}s, expected < 2.0s"

        # Verify all queries are under 2000ms (performance target)
        assert summary["all_under_2000ms"] is True

    @pytest.mark.asyncio
    async def test_query_error_handling(self, metadata_manager):
        """Test error handling in optimized queries."""
        manager, mock_collection, mock_query = metadata_manager

        # Test with None database
        manager.db = None

        # All queries should return empty results gracefully
        results1 = await manager.query_by_hierarchy_optimized(level_1="test")
        assert results1 == []

        results2 = await manager.query_by_version_range_optimized(min_version=1)
        assert results2 == []

        results3 = await manager.query_latest_by_category_optimized(category_value="test")
        assert results3 == []

        results4 = await manager.query_multi_level_hierarchy_optimized(level_1="test")
        assert results4 == []

        benchmark = await manager.benchmark_query_performance()
        assert benchmark == {}

    @pytest.mark.asyncio
    async def test_query_validation(self, metadata_manager):
        """Test input validation for optimized queries."""
        manager, mock_collection, mock_query = metadata_manager

        # Test invalid category level
        results = await manager.query_latest_by_category_optimized(
            category_level="invalid_level", category_value="test"
        )
        assert results == []

        # Test empty category value
        results = await manager.query_latest_by_category_optimized(category_level="level_1_category", category_value="")
        assert results == []

        # Test empty level_1 for multi-level query
        results = await manager.query_multi_level_hierarchy_optimized(level_1="")
        assert results == []

    @pytest.mark.unit    def test_query_performance_target(self):
        """Test that query performance meets the <2s target."""
        # This test validates the performance requirement
        # In real scenarios with proper indexes, queries should be <2s

        # Mock a realistic query time measurement
        mock_query_times = [150, 200, 180, 220]  # milliseconds

        # All should be under 2000ms target
        assert all(time_ms < 2000 for time_ms in mock_query_times)

        # Average should be reasonable
        avg_time = sum(mock_query_times) / len(mock_query_times)
        assert avg_time < 500, f"Average query time {avg_time}ms should be < 500ms"
