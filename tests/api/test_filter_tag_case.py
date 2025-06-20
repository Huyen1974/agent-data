import pytest



def test_filter_tag_case_insensitive(client_with_qdrant_override):

    payload = {
        "query_text": "modern astronomy discoveries",
        "top_k": 1,  # Expect only the best match
        "filter_tag": "SCIENCE",  # test case-insensitive behavior
        "score_threshold": 0.5,
    }
    resp = client_with_qdrant_override.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 200
    results = resp.json().get("results", [])
    assert len(results) == 1
    assert results[0]["payload"]["tag"].lower() == "science"
    # Optionally, also assert the ID if it's stable and known for this test
    assert results[0]["id"] == 9001
