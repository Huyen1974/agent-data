"""Test QdrantStore VectorStore interface implementation."""

import numpy as np
import pytest
from qdrant_client.http.models import Filter, FilterSelector

from tests.mocks.fake_qdrant_v2 import MockQdrantStore


@pytest.fixture
async def qdrant_store_mock():
    """Mock QdrantStore for testing."""
    store = MockQdrantStore()
    # Clear any existing data to ensure test isolation
    store.client.clear_all_data()
    return store


@pytest.mark.asyncio
async def test_points_selector_empty(qdrant_store_mock):
    """Test PointsSelector behavior with empty filter."""
    # Test that FilterSelector with empty filter doesn't cause union-type errors
    empty_filter = Filter(must=[])
    # Create filter_selector to verify no union-type errors occur
    FilterSelector(filter=empty_filter)

    # This should not raise TypeError with typing.Union
    result = await qdrant_store_mock.delete_vectors_by_tag("nonexistent_tag")

    assert result["success"] is True
    assert result["tag"] == "nonexistent_tag"


@pytest.mark.asyncio
async def test_points_selector_with_filter(qdrant_store_mock):
    """Test PointsSelector with actual filter conditions."""
    # Add a test vector
    test_vector = [0.1] * 1536
    await qdrant_store_mock.upsert_vector(
        vector_id="test_id",
        vector=test_vector,
        metadata={"category": "test"},
        tag="test_tag",
    )

    # Delete by tag (should use FilterSelector internally)
    result = await qdrant_store_mock.delete_vectors_by_tag("test_tag")

    assert result["success"] is True
    assert result["tag"] == "test_tag"

    # Verify deletion worked
    query_result = await qdrant_store_mock.query_vectors_by_tag("test_tag")
    assert len(query_result) == 0


@pytest.mark.asyncio
async def test_vector_store_interface_methods(qdrant_store_mock):
    """Test all VectorStore interface methods work correctly."""
    # Test health check
    health = await qdrant_store_mock.health_check()
    assert health is True

    # Test vector count (should be 0 initially)
    count = await qdrant_store_mock.get_vector_count()
    assert count == 0

    # Test upsert
    test_vector = np.array([0.1] * 1536)
    upsert_result = await qdrant_store_mock.upsert_vector(
        vector_id="test_vector",
        vector=test_vector,
        metadata={"type": "test"},
        tag="interface_test",
    )
    assert upsert_result["success"] is True

    # Test count after upsert
    count = await qdrant_store_mock.get_vector_count()
    assert count == 1

    # Test query
    query_result = await qdrant_store_mock.query_vectors_by_tag("interface_test")
    assert len(query_result) == 1
    assert query_result[0]["id"] == "test_vector"

    # Test delete
    delete_result = await qdrant_store_mock.delete_vectors_by_tag("interface_test")
    assert delete_result["success"] is True

    # Verify deletion
    final_count = await qdrant_store_mock.get_vector_count()
    assert final_count == 0
