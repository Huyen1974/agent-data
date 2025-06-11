from fastapi.testclient import TestClient
import pytest


@pytest.mark.deferred
def test_negative_top_k(client: TestClient):
    payload = {"query_text": "quick check", "top_k": -5, "score_threshold": 0.3}
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422  # FastAPI/Pydantic validation
    errors = resp.json()["detail"]
    # assert any("top_k" in err["loc"] and "must be > 0" in err["msg"] # Original incorrect assertion
    #            for err in errors)
    assert any(
        err.get("type") == "greater_than"
        and err.get("loc") == ["body", "top_k"]
        and "Input should be greater than 0" in err.get("msg", "")
        for err in errors
    )
