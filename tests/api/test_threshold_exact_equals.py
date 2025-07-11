from fastapi.testclient import TestClient
import pytest


@pytest.mark.unit
def test_threshold_exact_equals(client_with_qdrant_override: TestClient):
    response = client_with_qdrant_override.post(
        "/semantic_search_cosine",
        json={
            "query_text": "modern astronomy discoveries",
            "filter_tag": "science",
            "top_k": 1,
            "score_threshold": 1.0,
        },
    )
    assert response.status_code == 200
    results = response.json().get("results", [])
    assert len(results) == 1, f"Expected 1 result for exact threshold 1.0, got {len(results)}"
    assert results[0]["id"] == 9001, "Expected ID 9001 for 'modern astronomy discoveries'"
