from fastapi.testclient import TestClient
from agent_data_manager.tools.search_by_payload_tool import search_by_payload_sync
import pytest


    @pytest.mark.unitdef test_search_by_payload_valid(client_with_qdrant_override: TestClient):
    """Test search_by_payload with valid field and value."""
    result = search_by_payload_sync(collection_name="test_collection", field="tag", value="science", limit=5)
    assert result["status"] == "success"
    assert result["count"] > 0
    assert "results" in result
    assert isinstance(result["results"], list)
    # Verify that we found science-tagged items from the test data
    for item in result["results"]:
        assert "payload" in item
        assert item["payload"]["tag"] == "science"


    @pytest.mark.unitdef test_search_by_payload_empty_field():
    """Test search_by_payload with empty field."""
    result = search_by_payload_sync(collection_name="test_collection", field="", value="science")
    assert result["status"] == "failed"
    assert result["count"] == 0
    assert "error" in result
    assert "Field cannot be empty" in result["error"]


    @pytest.mark.unitdef test_search_by_payload_none_value():
    """Test search_by_payload with None value."""
    result = search_by_payload_sync(collection_name="test_collection", field="tag", value=None)
    assert result["status"] == "failed"
    assert result["count"] == 0
    assert "error" in result
    assert "Value cannot be None" in result["error"]


    @pytest.mark.unitdef test_search_by_payload_pagination(client_with_qdrant_override: TestClient):
    """Test search_by_payload with pagination using offset."""
    # First request with limit=2
    result1 = search_by_payload_sync(collection_name="test_collection", field="tag", value="science", limit=2)
    assert result1["status"] == "success"
    assert result1["count"] <= 2
    assert "results" in result1

    # If there are more results, test pagination
    if result1["next_offset"] is not None:
        next_offset = result1["next_offset"]
        result2 = search_by_payload_sync(
            collection_name="test_collection", field="tag", value="science", limit=2, offset=next_offset
        )
        assert result2["status"] == "success"
        assert "results" in result2
        # Ensure we get different results (no overlap in IDs)
        ids1 = {item["id"] for item in result1["results"]}
        ids2 = {item["id"] for item in result2["results"]}
        assert len(ids1.intersection(ids2)) == 0, "Pagination should return different results"
