import pytest


    @pytest.mark.unit
    def test_top_k_minimum_one(client_with_qdrant_override):

    payload = {"query_text": "historical events", "top_k": 1, "filter_tag": "history", "score_threshold": 0.0}
    resp = client_with_qdrant_override.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 200
    response_data = resp.json()
    assert "results" in response_data
    results_list = response_data["results"]
    assert isinstance(results_list, list)
    assert len(results_list) == 1
