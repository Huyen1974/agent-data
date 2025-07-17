import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_tag_too_long(client_with_qdrant_override: TestClient):
    long_tag = "x" * 65
    response = client_with_qdrant_override.post(
        "/semantic_search_cosine",
        json={
            "query_text": "modern astronomy discoveries",
            "filter_tag": long_tag,
            "top_k": 1,
            "score_threshold": 0.5,
        },
    )
    assert (
        response.status_code == 422
    ), f"Expected 422 for filter_tag length > 64, got {response.status_code}"
    error_detail = response.json().get("detail", [])
    assert any(
        detail.get("loc") == ["body", "filter_tag"]
        and "String should have at most 64 characters" in detail.get("msg", "")
        for detail in error_detail
    ), f"Expected specific filter_tag length validation error, got {error_detail}"
