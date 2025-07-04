import pytest



    @pytest.mark.unitdef test_query_text_blank_spaces(client):
    payload = {"query_text": "    ", "top_k": 3, "filter_tag": "science"}
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422
    errs = resp.json()["detail"]
    assert any(
        (
            err.get("loc") == ["body", "query_text"]
            and "query_text cannot be empty or just whitespace" in err.get("msg", "")
        )
        for err in errs
    ), f"Expected specific query_text validation error, got {errs}"
