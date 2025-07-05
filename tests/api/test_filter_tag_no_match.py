import pytest


    @pytest.mark.unit
    def test_filter_tag_with_no_matches(client_with_qdrant_override):

    payload = {
        "query_text": "science topics",
        "top_k": 5,
        "filter_tag": "nonexistent-tag",  # This tag doesn't match any mock data
        "score_threshold": 0.0,
    }
    resp = client_with_qdrant_override.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, dict)
    assert results.get("results") == []
