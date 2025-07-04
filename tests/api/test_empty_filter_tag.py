import pytest


    @pytest.mark.unitdef test_empty_filter_tag_rejected(client):

    payload = {
        "query_text": "explain climate science",
        "top_k": 3,
        "filter_tag": "",  # Invalid: empty string
        "score_threshold": 0.3,
    }
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422
    errs = resp.json()["detail"]
    assert any(
        (
            err.get("loc") == ["body", "filter_tag"]
            and ("filter_tag, if provided, cannot be empty or just whitespace" in err.get("msg", ""))
        )
        for err in errs
    ), f"Test for empty string failed. Expected specific filter_tag error, got {errs}"


    @pytest.mark.unitdef test_whitespace_filter_tag_rejected(client):
    payload = {
        "query_text": "explain climate science",
        "top_k": 3,
        "filter_tag": "   ",  # Invalid: whitespace
        "score_threshold": 0.3,
    }
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422
    errs = resp.json()["detail"]
    assert any(
        (
            err.get("loc") == ["body", "filter_tag"]
            and ("filter_tag, if provided, cannot be empty or just whitespace" in err.get("msg", ""))
        )
        for err in errs
    ), f"Test for whitespace string failed. Expected specific filter_tag error, got {errs}"
