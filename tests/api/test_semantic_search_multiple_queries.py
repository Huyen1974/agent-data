from fastapi.testclient import TestClient
import pytest


    @pytest.mark.slowdef test_semantic_search_multiple_queries(client_with_qdrant_override: TestClient):
    queries = [
        {"query_text": "modern astronomy discoveries", "expected_id": 9001},
        {"query_text": "deep space exploration", "expected_id": 1001},
    ]
    for query in queries:
        response = client_with_qdrant_override.post(
            "/semantic_search_cosine",
            json={
                "query_text": query["query_text"],
                "filter_tag": "science",
                "top_k": 1,
                "score_threshold": 0.5,
            },
        )
        assert response.status_code == 200
        results = response.json().get("results", [])
        assert len(results) == 1, f"Expected 1 result for '{query['query_text']}', got {len(results)}"
        assert (
            results[0]["id"] == query["expected_id"]
        ), f"Expected ID {query['expected_id']} for '{query['query_text']}'"
