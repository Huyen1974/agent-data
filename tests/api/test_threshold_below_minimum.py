import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_threshold_below_minimum(client_with_qdrant_override: TestClient):
    response = client_with_qdrant_override.post(
        "/semantic_search_cosine",
        json={
            "query_text": "extremely obscure and irrelevant query string for testing purposes",
            "filter_tag": "science",
            "top_k": 1,
            "score_threshold": 0.99,
        },
    )
    assert response.status_code == 200
    results = response.json().get("results", [])
    assert (
        len(results) == 0
    ), f"Expected 0 results for threshold 0.99, got {len(results)}"
