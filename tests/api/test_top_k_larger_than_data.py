import pytest



def test_top_k_exceeds_data_count(client_with_qdrant_override):

    payload = {
        "query_text": "modern astronomy discoveries",
        "top_k": 10,
        "filter_tag": "science",
        "score_threshold": 0.0,
    }
    resp = client_with_qdrant_override.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, dict)
    assert len(results.get("results", [])) == 4  # Expect all 4 science entries
