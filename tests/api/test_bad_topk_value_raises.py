from fastapi.testclient import TestClient
import pytest


@pytest.mark.deferred
def test_bad_topk_value_raises(client_with_qdrant_override: TestClient):
    for invalid_top_k in [0, -1]:
        response = client_with_qdrant_override.post(
            "/semantic_search_cosine",
            json={
                "query_text": "modern astronomy discoveries",
                "filter_tag": "science",
                "top_k": invalid_top_k,
                "score_threshold": 0.5,
            },
        )
        assert response.status_code == 422, f"Expected 422 for top_k={invalid_top_k}, got {response.status_code}"

        error_detail = response.json().get("detail")
        assert isinstance(error_detail, list) and len(error_detail) > 0, "Error detail should be a non-empty list"

        found_error = False
        for error in error_detail:
            if error.get("loc") == ["body", "top_k"] and "Input should be greater than 0" in error.get("msg", ""):
                found_error = True
                break
        assert (
            found_error
        ), f"Expected specific top_k validation error message for top_k={invalid_top_k}, got {error_detail}"
