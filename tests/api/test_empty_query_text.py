import pytest



    @pytest.mark.unitdef test_empty_query_text(client):

    payload = {"query_text": "", "top_k": 3, "score_threshold": 0.4}  # invalid – empty
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422  # Pydantic validation
    errors = resp.json()["detail"]
    assert any(
        "query_text" in err["loc"] and ("empty" in err["msg"] or "must not be blank" in err["msg"]) for err in errors
    )
