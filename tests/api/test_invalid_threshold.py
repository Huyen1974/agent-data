import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_invalid_score_threshold(client: TestClient):
    response = client.post(
        "/semantic_search_cosine",
        json={"query_text": "test", "top_k": 3, "score_threshold": 1.5},
    )
    assert response.status_code == 422
    error_details = response.json()["detail"]
    assert isinstance(error_details, list)
    assert any(
        "score_threshold must be between 0 and 1" in error.get("msg", "")
        for error in error_details
    )
