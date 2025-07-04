#!/usr/bin/env python
"""Test suite for the DELETE_BY_TAG endpoint functionality."""

import pytest
from fastapi.testclient import TestClient

from agent_data_manager.tools.delete_by_tag_tool import delete_by_tag_sync


    @pytest.mark.unitdef test_delete_by_tag_valid(client_with_qdrant_override: TestClient):
    """
    Test DELETE_BY_TAG with a valid tag that exists in the data.
    Should successfully delete vectors with the specified tag.
    """
    # The client_with_qdrant_override fixture seeds data with tags like "science", "cooking", "history"
    # Let's delete vectors with the "science" tag
    result = delete_by_tag_sync("science")

    assert result["status"] == "success"
    assert result["deleted_count"] > 0
    assert "message" in result
    assert "science" in result["message"]


    @pytest.mark.unitdef test_delete_by_tag_empty():
    """
    Test DELETE_BY_TAG with empty or whitespace-only tag.
    Should fail with appropriate error message.
    """
    # Test empty string
    result = delete_by_tag_sync("")
    assert result["status"] == "failed"
    assert result["deleted_count"] == 0
    assert "error" in result
    assert "empty" in result["error"].lower()

    # Test whitespace-only string
    result = delete_by_tag_sync("   ")
    assert result["status"] == "failed"
    assert result["deleted_count"] == 0
    assert "error" in result
    assert "empty" in result["error"].lower() or "whitespace" in result["error"].lower()


    @pytest.mark.unitdef test_delete_by_tag_non_existent(client_with_qdrant_override: TestClient):
    """
    Test DELETE_BY_TAG with a tag that doesn't exist in the data.
    Should succeed but delete 0 vectors.
    """
    # Use a tag that doesn't exist in the seeded data
    result = delete_by_tag_sync("non_existent_tag_12345")

    assert result["status"] == "success"
    assert result["deleted_count"] == 0
    assert "message" in result
    assert "non_existent_tag_12345" in result["message"]
