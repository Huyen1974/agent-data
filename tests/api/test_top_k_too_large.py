import pytest


    @pytest.mark.unitdef test_top_k_too_large(client):

    payload = {"query_text": "limit check", "top_k": 200, "score_threshold": 0.3}  # over maximum
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422
    errors = resp.json()["detail"]
    assert any(
        "top_k" in err["loc"] and ("100" in err["msg"] or "≤" in err["msg"] or "less than or equal to" in err["msg"])
        for err in errors
    )
