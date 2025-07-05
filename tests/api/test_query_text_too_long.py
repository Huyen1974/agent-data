import pytest


    @pytest.mark.unit
    def test_query_text_exceeds_max_length(client):

    long_text = "x" * 3000
    payload = {"query_text": long_text, "top_k": 3, "filter_tag": "science", "score_threshold": 0.3}
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422
    errs = resp.json()["detail"]
    assert any(
        ("query_text" in err["loc"]) and ("String should have at most" in err["msg"] and "characters" in err["msg"])
        for err in errs
    )
