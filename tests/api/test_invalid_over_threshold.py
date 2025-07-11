import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_score_threshold_over_one(client: TestClient):
    payload = {"query_text": "edge-case check", "top_k": 3, "score_threshold": 1.5}  # invalid (>1)
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422  # Pydantic validation
    errors = resp.json()["detail"]
    assert any("score_threshold" in err["loc"] and ("<=" in err["msg"] or "must be" in err["msg"]) for err in errors)
