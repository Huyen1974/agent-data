import pytest


@pytest.mark.unit
def test_filter_tag_required_when_no_threshold(client):

    payload = {
        "query_text": "great galaxies",
        "top_k": 5,
        # score_threshold omitted
        # filter_tag omitted  -> should error
    }
    resp = client.post("/semantic_search_cosine", json=payload)
    assert resp.status_code == 422
    errs = resp.json()["detail"]
    assert any(
        ("filter_tag" in err["loc"] or "filter_tag" in err.get("msg", ""))
        and ("required" in err["msg"] or "must be provided" in err["msg"])
        for err in errs
    )
