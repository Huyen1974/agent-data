import pytest


@pytest.mark.deferred
def test_score_threshold_one(client_with_qdrant_override):

    payload = {
        "query_text": "modern astronomy discoveries",  # matches point 9001 exactly
        "top_k": 3,
        "filter_tag": "science",
        "score_threshold": 1.0,
    }
    resp = client_with_qdrant_override.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, dict)
    assert len(results.get("results", [])) == 1
    assert results["results"][0]["id"] == 9001
