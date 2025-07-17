import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
@pytest.mark.unit
def test_empty_query_rejected(client_with_qdrant_override: TestClient):
    for invalid_query in ["", "   "]:
        response = client_with_qdrant_override.post(
            "/semantic_search_cosine",
            json={
                "query_text": invalid_query,
                "filter_tag": "science",
                "top_k": 1,
                "score_threshold": 0.5,
            },
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 for query_text='{invalid_query}', got {response.status_code}"
        error_detail = response.json().get("detail", [])
        assert any(
            "query_text cannot be empty or just whitespace" in detail.get("msg", "")
            for detail in error_detail
        ), f"Expected empty query error for query_text='{invalid_query}'"
