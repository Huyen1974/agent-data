#!/usr/bin/env python
"""Test suite for the BULK_UPLOAD endpoint functionality."""
import sys
import os
from fastapi.testclient import TestClient
import pytest

# Adjust sys.path to include the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agent_data_manager.tools.bulk_upload_tool import bulk_upload_sync


    @pytest.mark.slowdef test_bulk_upload_valid(client_with_qdrant_override: TestClient):
    """
    Test BULK_UPLOAD with valid points.
    Should successfully upload vectors to the collection.
    """
    points = [
        {"vector": [0.1] * 1536, "payload": {"tag": "test1", "content": "First test point"}},
        {"vector": [0.2] * 1536, "payload": {"tag": "test2", "content": "Second test point"}},
    ]

    result = bulk_upload_sync("test_collection", points)

    assert result["status"] == "success"
    assert result["uploaded_count"] == 2
    assert "message" in result
    assert "test_collection" in result["message"]


    @pytest.mark.slowdef test_bulk_upload_empty_collection():
    """
    Test BULK_UPLOAD with empty or whitespace-only collection name.
    Should fail with appropriate error message.
    """
    points = [{"vector": [0.1] * 1536, "payload": {"tag": "test"}}]

    # Test empty string
    result = bulk_upload_sync("", points)
    assert result["status"] == "failed"
    assert result["uploaded_count"] == 0
    assert "error" in result
    assert "empty" in result["error"].lower() or "whitespace" in result["error"].lower()

    # Test whitespace-only string
    result = bulk_upload_sync("   ", points)
    assert result["status"] == "failed"
    assert result["uploaded_count"] == 0
    assert "error" in result
    assert "empty" in result["error"].lower() or "whitespace" in result["error"].lower()


    @pytest.mark.slowdef test_bulk_upload_empty_points():
    """
    Test BULK_UPLOAD with empty points list.
    Should fail with appropriate error message.
    """
    result = bulk_upload_sync("test_collection", [])

    assert result["status"] == "failed"
    assert result["uploaded_count"] == 0
    assert "error" in result
    assert "empty" in result["error"].lower()


    @pytest.mark.slowdef test_bulk_upload_invalid_points(client_with_qdrant_override: TestClient):
    """
    Test BULK_UPLOAD with invalid points (missing vector).
    Should fail with appropriate error message.
    """
    points = [
        {"payload": {"tag": "test1"}},  # Missing vector
        {"vector": "not_a_list", "payload": {"tag": "test2"}},  # Invalid vector type
    ]

    result = bulk_upload_sync("test_collection", points)

    assert result["status"] == "failed"
    assert result["uploaded_count"] == 0
    assert "error" in result
    assert "valid" in result["error"].lower()


    @pytest.mark.slowdef test_bulk_upload_mixed_valid_invalid(client_with_qdrant_override: TestClient):
    """
    Test BULK_UPLOAD with a mix of valid and invalid points.
    Should upload only the valid points.
    """
    points = [
        {"vector": [0.1] * 1536, "payload": {"tag": "valid1", "content": "Valid point"}},
        {"payload": {"tag": "invalid"}},  # Missing vector
        {"vector": [0.2] * 1536, "payload": {"tag": "valid2", "content": "Another valid point"}},
    ]

    result = bulk_upload_sync("test_collection", points)

    assert result["status"] == "success"
    assert result["uploaded_count"] == 2  # Only the valid points should be uploaded


    @pytest.mark.slowdef test_bulk_upload_with_custom_ids(client_with_qdrant_override: TestClient):
    """
    Test BULK_UPLOAD with custom point IDs.
    Should successfully upload vectors with the specified IDs.
    """
    points = [
        {"id": 12345, "vector": [0.1] * 1536, "payload": {"tag": "custom_id_test", "content": "Point with custom ID"}}
    ]

    result = bulk_upload_sync("test_collection", points)

    assert result["status"] == "success"
    assert result["uploaded_count"] == 1
    assert "message" in result
