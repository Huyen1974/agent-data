import pytest
from fastapi.testclient import TestClient
import random
from typing import List, Dict, Any
from unittest.mock import patch  # Added for mocking

# Assuming your FastAPI app instance is named `app` in `api_vector_search.py`
# and qdrant_store is accessible for direct interaction or mocking if needed.
# Adjust the import path according to your project structure.
from api_vector_search import (
    app,
)  # app from main API file. Removed OPENAI_EMBEDDING_MODEL import as it's not directly used here now.

client = TestClient(app)

EXPECTED_EMBEDDING_DIMENSION = 1536  # Define if not already imported


def generate_dummy_embedding(seed: int = None) -> List[float]:
    if seed is not None:
        random.seed(seed)
    # Generate a vector that looks like a normalized embedding to better mimic real ones
    vec = [random.uniform(-1.0, 1.0) for _ in range(EXPECTED_EMBEDDING_DIMENSION)]
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return [0.0] * EXPECTED_EMBEDDING_DIMENSION
    return [x / norm for x in vec]


async def mock_generate_openai_embedding(text: str, model: str = None) -> Dict[str, Any]:
    seed = None
    if text == "The study of stars and celestial bodies.":
        seed = 1
    elif text == "Exploring galaxies and cosmic phenomena.":
        seed = 2
    elif "astronomy and space exploration" in text and "Tell me about" in text:
        seed = 5
    # Fallback for any other text to ensure some vector is always returned
    else:
        seed = sum(ord(c) for c in text) % 2000  # Hash-like seed for other texts

    return {"embedding": generate_dummy_embedding(seed=seed), "model": "mock_model_for_score_tests", "text": text}


def create_vector_item(id_val: Any, tag: str, text: str, seed: int = None) -> Dict[str, Any]:
    return {
        "id": id_val,
        "vector": generate_dummy_embedding(seed=seed),
        "metadata": {"tag": tag, "original_text": text, "source": "test_score_threshold"},
    }


# Changed scope to function, removed autouse. Tests will request it explicitly.
@pytest.fixture(scope="function")
def setup_test_vectors(client):  # Added client fixture dependency
    test_module_tag = "test_score_threshold_module_data"
    start_id = 9000
    vector_ids = [start_id + i for i in range(4)]

    vectors_to_insert = [
        create_vector_item(vector_ids[0], test_module_tag, "The study of stars and celestial bodies.", seed=1),
        create_vector_item(vector_ids[1], test_module_tag, "Exploring galaxies and cosmic phenomena.", seed=2),
        create_vector_item(vector_ids[2], test_module_tag, "Understanding planetary motion and orbits.", seed=3),
        create_vector_item(vector_ids[3], test_module_tag, "A brief history of culinary arts.", seed=4),
    ]

    for vec_item in vectors_to_insert:
        upsert_payload = {"point_id": vec_item["id"], "vector": vec_item["vector"], "metadata": vec_item["metadata"]}
        response_insert = client.post("/upsert_vector", json=upsert_payload)
        assert response_insert.status_code == 200, f"Upsert failed for {vec_item['id']}: {response_insert.text}"
        assert response_insert.json().get("status") == "ok"

    yield  # Test cases run here

    # Teardown: Delete the test vectors by tag.
    # This is important for function-scoped fixture if not relying on global clear in conftest
    # However, _reset_qdrant_state_before_each_test in conftest.py should handle data clearing.
    # Keeping this explicit delete-by-tag can be a good safeguard or for specific logic.
    # For now, let's rely on the global clear in conftest.py, so this can be commented or removed
    # if it causes issues with FakeQdrantClient's delete_collection logic.
    # response_delete = client.post("/delete_vectors_by_tag", json={"tag": test_module_tag})
    # assert response_delete.status_code == 200, f"Delete by tag failed: {response_delete.text}"


@patch("api_vector_search._generate_openai_embedding", new=mock_generate_openai_embedding)
def test_query_vectors_by_score_threshold_passes(setup_test_vectors, client):
    query_text = "The study of stars and celestial bodies."
    score_threshold = 0.95
    test_module_tag = "test_score_threshold_module_data"

    response = client.post(
        "/semantic_search_cosine",
        json={"query_text": query_text, "top_k": 4, "filter_tag": test_module_tag, "score_threshold": score_threshold},
    )
    assert response.status_code == 200, f"Error: {response.text}"
    response_data = response.json()
    assert response_data["status"] == "ok"

    results = response_data["results"]
    assert (
        len(results) > 0
    ), f"Expected at least one result with threshold {score_threshold} for query '{query_text}', got {len(results)}. Full response: {response_data}"

    found_matching_text = False
    for item in results:
        assert "id" in item
        assert "score" in item
        assert "payload" in item
        assert (
            item["score"] >= score_threshold
        ), f"Vector {item['id']} score {item['score']} is below threshold {score_threshold}. Query text: '{query_text}'"
        assert item["payload"].get("source") == "test_score_threshold"
        if item["payload"].get("original_text") == query_text:
            found_matching_text = True
            assert item["id"] == 9000
    assert (
        found_matching_text
    ), f"Did not find the exact matching text '{query_text}' in results above threshold {score_threshold}."


@patch("api_vector_search._generate_openai_embedding", new=mock_generate_openai_embedding)
def test_query_vectors_by_score_threshold_filters_all(setup_test_vectors, client):
    query_text = "Tell me about astronomy and space exploration."
    score_threshold = 0.99
    test_module_tag = "test_score_threshold_module_data"

    response = client.post(
        "/semantic_search_cosine",
        json={"query_text": query_text, "top_k": 4, "filter_tag": test_module_tag, "score_threshold": score_threshold},
    )
    assert response.status_code == 200, f"Error: {response.text}"
    response_data = response.json()
    assert response_data["status"] == "ok"

    results = response_data["results"]
    assert (
        len(results) == 0
    ), f"Expected 0 results with threshold {score_threshold}, got {len(results)}. Query: '{query_text}'"


@patch("api_vector_search._generate_openai_embedding", new=mock_generate_openai_embedding)
def test_query_vectors_without_score_threshold(setup_test_vectors, client):
    query_text = "The study of stars and celestial bodies."
    test_module_tag = "test_score_threshold_module_data"

    response = client.post(
        "/semantic_search_cosine", json={"query_text": query_text, "top_k": 1, "filter_tag": test_module_tag}
    )
    assert response.status_code == 200, f"Error: {response.text}"
    response_data = response.json()
    assert response_data["status"] == "ok"

    results = response_data["results"]
    assert len(results) > 0, "Expected results when score_threshold is omitted."

    if results:
        assert results[0]["payload"].get("source") == "test_score_threshold"
        assert results[0]["payload"].get("original_text") == query_text
        assert results[0]["id"] == 9000
        assert results[0]["score"] > 0.95, "Self-match score too low without thresholding"

    print(f"PASS: test_query_vectors_without_score_threshold - Found {len(results)} item(s) when threshold omitted.")
