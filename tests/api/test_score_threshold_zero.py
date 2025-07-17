import pytest


@pytest.mark.unit
def test_score_threshold_zero(client_with_qdrant_override):

    payload = {
        "query_text": "example about science",
        "top_k": 5,
        "score_threshold": 0.0,
        "filter_tag": "science",
    }
    resp = client_with_qdrant_override.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 200
    result = resp.json()
    assert isinstance(result, dict)
    assert "results" in result
