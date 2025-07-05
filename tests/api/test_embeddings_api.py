#!/usr/bin/env python
"""Test suite for the embeddings API, focusing on semantic search and vector management."""
import uuid
import sys
import os
from unittest.mock import patch
from typing import Dict, List, Any, Union

from fastapi.testclient import TestClient
import pytest

# Adjust sys.path to include the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import after sys.path modification
from api_vector_search import app, _generate_openai_embedding  # noqa: E402
from agent_data_manager.vector_store.base import VectorStore  # noqa: E402

# Expected dimension for OpenAI's text-embedding-ada-002 model
EXPECTED_EMBEDDING_DIMENSION = 1536
OPENAI_API_KEY_AVAILABLE = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("OPENAI_API_KEY") != "dummy"


# Helper to generate unique tags for tests
def generate_unique_tag(prefix="test-emb"):
    return f"{prefix}-{uuid.uuid4()}"


# --- Mock VectorStore Implementation ---
class MockVectorStore(VectorStore):
    """Mock implementation of VectorStore interface for testing."""

    def __init__(self):
        self.vectors = {}  # Dict[str, Dict] - stores vector data by ID
        self.vector_count = 0

    async def upsert_vector(
        self, vector_id: str, vector: Union[List[float], Any], metadata: Dict[str, Any] = None, tag: str = None
    ) -> Dict[str, Any]:
        """Mock upsert_vector implementation."""
        if isinstance(vector, list):
            vector_data = vector
        else:
            vector_data = vector.tolist() if hasattr(vector, "tolist") else list(vector)

        self.vectors[str(vector_id)] = {"id": vector_id, "vector": vector_data, "metadata": metadata or {}, "tag": tag}
        self.vector_count = len(self.vectors)
        return {"status": "ok", "upserted": True}

    async def query_vectors_by_tag(
        self, tag: str, query_vector: Union[List[float], Any] = None, limit: int = 10, threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Mock query_vectors_by_tag implementation."""
        results = []
        for vector_data in self.vectors.values():
            if vector_data.get("tag") == tag:
                # Simple cosine similarity mock based on vector content
                score = self._calculate_mock_score(query_vector, vector_data["vector"], vector_data["metadata"])
                if score >= threshold:
                    results.append(
                        {
                            "id": vector_data["id"],
                            "score": score,
                            "payload": vector_data["metadata"],
                            "vector": vector_data["vector"],
                        }
                    )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def delete_vectors_by_tag(self, tag: str) -> Dict[str, Any]:
        """Mock delete_vectors_by_tag implementation."""
        deleted_count = 0
        to_delete = []
        for vector_id, vector_data in self.vectors.items():
            if vector_data.get("tag") == tag:
                to_delete.append(vector_id)

        for vector_id in to_delete:
            del self.vectors[vector_id]
            deleted_count += 1

        self.vector_count = len(self.vectors)
        return {"status": "ok", "deleted_count": deleted_count}

    async def get_vector_count(self) -> int:
        """Mock get_vector_count implementation."""
        return self.vector_count

    async def health_check(self) -> bool:
        """Mock health_check implementation."""
        return True

    def _calculate_mock_score(
        self, query_vector: List[float], stored_vector: List[float], metadata: Dict[str, Any]
    ) -> float:
        """Calculate a mock similarity score based on content matching."""
        if not query_vector or not stored_vector:
            return 0.0

        # Determine query category based on first non-zero dimension
        query_category = 0
        for i, val in enumerate(query_vector):
            if val > 0.5:  # Threshold for significant value
                query_category = i
                break

        # Determine stored category based on first non-zero dimension
        stored_category = 0
        for i, val in enumerate(stored_vector):
            if val > 0.5:
                stored_category = i
                break

        # High score if categories match
        if query_category == stored_category:
            return 0.95
        else:
            return 0.1

    def clear_all_data(self):
        """Clear all stored vectors."""
        self.vectors.clear()
        self.vector_count = 0


# --- Mock for OpenAI Embedding Generation ---
async def mock_generate_openai_embedding(text: str, model: str = "text-embedding-ada-002"):
    """Mocks the _generate_openai_embedding function to return hardcoded orthogonal vectors."""
    seed_val = 0  # Default category if no keywords match
    text_lower = text.lower()

    # Determine category based on text keywords
    if any(
        keyword in text_lower
        for keyword in ["star", "celestial", "galaxies", "nebulae", "atmosphere", "astronomy", "space"]
    ):
        seed_val = 1  # Science category
    elif any(keyword in text_lower for keyword in ["rome", "emperors", "renaissance", "art", "historical", "history"]):
        seed_val = 2  # History category
    elif any(keyword in text_lower for keyword in ["baking", "sourdough", "bread", "pastry", "cooking"]):
        seed_val = 3  # Cooking category
    elif any(keyword in text_lower for keyword in ["politics", "south america"]):
        seed_val = 4  # Politics category (for unrelated query)
    else:
        seed_val = 5  # Fallback/Other category for any other text

    # Create a base vector of zeros, pre-normalized (length 1 if one element is 1.0)
    embedding_vector = [0.0] * EXPECTED_EMBEDDING_DIMENSION

    # Set a unique dimension to 1.0 based on the category seed_val
    if seed_val == 1 and EXPECTED_EMBEDDING_DIMENSION > 0:
        embedding_vector[0] = 1.0
    elif seed_val == 2 and EXPECTED_EMBEDDING_DIMENSION > 1:
        embedding_vector[1] = 1.0
    elif seed_val == 3 and EXPECTED_EMBEDDING_DIMENSION > 2:
        embedding_vector[2] = 1.0
    elif seed_val == 4 and EXPECTED_EMBEDDING_DIMENSION > 3:
        embedding_vector[3] = 1.0
    elif seed_val == 5 and EXPECTED_EMBEDDING_DIMENSION > 4:
        embedding_vector[4] = 1.0

    return {"embedding": embedding_vector, "model": model, "text": text}


    @pytest.mark.slow
    def test_generate_embedding_mock():
    """
    Tests the /generate_embedding_real endpoint with mocked OpenAI API.
    - Sends text.
    - Expects a valid embedding in response.
    - Confirms embedding dimension.
    """
    from unittest.mock import patch

    local_client = TestClient(app)
    test_text = "This is a test sentence for generating an embedding."
    request_payload = {"text": test_text}

    # Mock the OpenAI embedding generation
    mock_embedding = [0.1] * EXPECTED_EMBEDDING_DIMENSION

    with patch("api_vector_search.openai.embeddings.create") as mock_openai:
        # Mock the OpenAI client response
        mock_openai_response = type(
            "MockResponse",
            (),
            {"data": [type("MockData", (), {"embedding": mock_embedding})()], "model": "text-embedding-ada-002"},
        )()
        mock_openai.return_value = mock_openai_response

        response = local_client.post("/generate_embedding_real", json=request_payload)

        assert (
            response.status_code == 200
        ), f"Expected status 200, got {response.status_code}. Response: {response.text}"

        response_json = response.json()

        assert "text" in response_json
        assert response_json["text"] == test_text

        assert "embedding" in response_json
        assert isinstance(response_json["embedding"], list)
        assert (
            len(response_json["embedding"]) == EXPECTED_EMBEDDING_DIMENSION
        ), f"Expected embedding dimension {EXPECTED_EMBEDDING_DIMENSION}, got {len(response_json['embedding'])}"

        assert "model" in response_json
        assert isinstance(response_json["model"], str)


@pytest.mark.skipif(not OPENAI_API_KEY_AVAILABLE, reason="OPENAI_API_KEY not set, skipping real embedding tests")
    @pytest.mark.slow
    def test_generate_embedding_real():
    """
    Tests the /generate_embedding_real endpoint.
    - Sends text.
    - Expects a valid embedding in response.
    - Confirms embedding dimension.
    """
    local_client = TestClient(app)

    test_text = "This is a test sentence for generating an embedding."
    request_payload = {"text": test_text}

    response = local_client.post("/generate_embedding_real", json=request_payload)

    assert response.status_code == 200, f"Expected status 200, got {response.status_code}. Response: {response.text}"

    response_json = response.json()

    assert "text" in response_json
    assert response_json["text"] == test_text

    assert "embedding" in response_json
    assert isinstance(response_json["embedding"], list)
    assert (
        len(response_json["embedding"]) == EXPECTED_EMBEDDING_DIMENSION
    ), f"Expected embedding dimension {EXPECTED_EMBEDDING_DIMENSION}, got {len(response_json['embedding'])}"
    assert all(
        isinstance(x, float) for x in response_json["embedding"]
    ), "All elements in the embedding list should be floats."

    assert "model" in response_json
    assert isinstance(response_json["model"], str)
    assert "text-embedding-ada-002" in response_json["model"].lower()


@pytest.fixture(scope="function")
def mock_vector_store():
    """Fixture that provides a mock VectorStore instance."""
    return MockVectorStore()


@pytest.fixture(scope="function")
def setup_qdrant_for_search_tests(client_with_qdrant_override: TestClient, mock_vector_store: MockVectorStore):
    """
    Fixture to ensure VectorStore is clean and populated for search tests.
    Uses mock VectorStore instead of real Qdrant.
    """
    import asyncio

    # Clear any existing data
    mock_vector_store.clear_all_data()

    test_data = [
        {"id": 1001, "text": "The study of stars and celestial bodies.", "tag": "science"},
        {"id": 1002, "text": "Exploring distant galaxies and nebulae.", "tag": "science"},
        {"id": 1003, "text": "The composition of the Earth's atmosphere.", "tag": "science"},
        {"id": 2001, "text": "Ancient Rome and its powerful emperors.", "tag": "history"},
        {"id": 2002, "text": "The impact of the Renaissance on European art.", "tag": "history"},
        {"id": 3001, "text": "A guide to baking delicious sourdough bread.", "tag": "cooking"},
        {"id": 3002, "text": "Advanced techniques for French pastry.", "tag": "cooking"},
    ]
    all_upserted_ids = []

    # Mock the VectorStore dependency
    with patch("api_vector_search.get_qdrant_store", return_value=mock_vector_store):
        # Override the embedding function
        app.dependency_overrides[_generate_openai_embedding] = mock_generate_openai_embedding

        try:
            for item in test_data:
                # Generate embedding using mock function directly
                embedding_result = asyncio.run(mock_generate_openai_embedding(item["text"]))
                embedding = embedding_result["embedding"]

                # Upsert into mock VectorStore
                upsert_payload = {
                    "point_id": item["id"],
                    "vector": embedding,
                    "metadata": {"original_text": item["text"], "tag": item["tag"]},
                }
                resp = client_with_qdrant_override.post("/upsert_vector", json=upsert_payload)
                if resp.status_code != 200:
                    pytest.fail(f"Failed to upsert vector for setup: {item['id']} - {resp.text}")
                all_upserted_ids.append(item["id"])

            yield {"upserted_ids": all_upserted_ids, "test_data_map": {item["id"]: item for item in test_data}}

        finally:
            app.dependency_overrides.pop(_generate_openai_embedding, None)


    @pytest.mark.slow
    def test_semantic_search_cosine(
    setup_qdrant_for_search_tests, client_with_qdrant_override: TestClient, mock_vector_store: MockVectorStore
):
    """
    Tests the /semantic_search_cosine endpoint with mocked VectorStore.
    """
    with patch("api_vector_search.get_qdrant_store", return_value=mock_vector_store):
        app.dependency_overrides[_generate_openai_embedding] = mock_generate_openai_embedding
        try:
            query_text_science = "learning about astronomy and space exploration"
            search_payload_science = {"query_text": query_text_science, "top_k": 3, "filter_tag": "science"}
            response_science = client_with_qdrant_override.post("/semantic_search_cosine", json=search_payload_science)

            assert response_science.status_code == 200, response_science.text
            results_science = response_science.json()["results"]
            assert len(results_science) > 0, "Expected science results for 'astronomy' query"
            assert (
                results_science[0]["payload"]["tag"] == "science"
            ), f"Top result for 'astronomy' should be science. Got: {results_science[0]}"
            scores_science = [res["score"] for res in results_science]
            assert all(
                scores_science[i] >= scores_science[i + 1] for i in range(len(scores_science) - 1)
            ), f"Science search results not sorted by score (descending): {scores_science}"

            query_text_history = "information about historical events and figures"
            search_payload_history = {"query_text": query_text_history, "top_k": 2, "filter_tag": "history"}
            response_history = client_with_qdrant_override.post("/semantic_search_cosine", json=search_payload_history)

            assert response_history.status_code == 200, response_history.text
            results_history = response_history.json()["results"]
            assert len(results_history) > 0, "Expected history results for 'historical events' query"
            assert (
                results_history[0]["payload"]["tag"] == "history"
            ), f"Top result for 'historical events' should be history. Got: {results_history[0]}"
            scores_history = [res["score"] for res in results_history]
            assert all(
                scores_history[i] >= scores_history[i + 1] for i in range(len(scores_history) - 1)
            ), f"History search results not sorted by score (descending): {scores_history}"

            query_text_baking = "how to bake bread"
            search_payload_cooking_tagged = {"query_text": query_text_baking, "top_k": 2, "filter_tag": "cooking"}
            response_cooking_tagged = client_with_qdrant_override.post(
                "/semantic_search_cosine", json=search_payload_cooking_tagged
            )

            assert response_cooking_tagged.status_code == 200, response_cooking_tagged.text
            results_cooking_tagged = response_cooking_tagged.json()["results"]
            assert len(results_cooking_tagged) > 0, "Expected cooking results for 'baking' query with tag filter"
            for res in results_cooking_tagged:
                assert (
                    res["payload"]["tag"] == "cooking"
                ), f"Result for 'baking' with tag 'cooking' has wrong tag: {res['payload']['tag']}"

            query_text_unrelated = "modern politics in South America"
            search_payload_unrelated = {"query_text": query_text_unrelated, "top_k": 3, "filter_tag": "politics"}
            response_unrelated = client_with_qdrant_override.post(
                "/semantic_search_cosine", json=search_payload_unrelated
            )

            assert response_unrelated.status_code == 200, response_unrelated.text
        finally:
            app.dependency_overrides.pop(_generate_openai_embedding, None)


    @pytest.mark.slow
    def test_clear_embeddings(
    setup_qdrant_for_search_tests, client_with_qdrant_override: TestClient, mock_vector_store: MockVectorStore
):
    """
    Tests the /clear_embeddings endpoint with mocked VectorStore.
    """
    with patch("api_vector_search.get_qdrant_store", return_value=mock_vector_store):
        app.dependency_overrides[_generate_openai_embedding] = mock_generate_openai_embedding
        try:
            upserted_data_info = setup_qdrant_for_search_tests
            initial_upserted_ids = upserted_data_info["upserted_ids"]
            num_initial_items = len(initial_upserted_ids)

            assert num_initial_items > 0, "Fixture should have upserted some items for clear test"

            response = client_with_qdrant_override.post("/clear_embeddings")
            assert (
                response.status_code == 200
            ), f"Expected status 200 for /clear_embeddings, got {response.status_code}. Response: {response.text}"

            response_json = response.json()
            assert "status" in response_json and response_json["status"] == "ok"
            assert "deleted_count" in response_json
            # Be flexible about the deletion count since the mock store may have data from other tests
            assert (
                response_json["deleted_count"] >= num_initial_items
            ), f"Expected to delete at least {num_initial_items} items, but /clear_embeddings reported {response_json['deleted_count']}"

            if initial_upserted_ids:
                test_id_to_check = initial_upserted_ids[0]
                get_response = client_with_qdrant_override.post(
                    "/get_vector_by_id", json={"point_id": test_id_to_check}
                )
                assert (
                    get_response.status_code == 404
                ), f"Expected 404 (Not Found) for ID {test_id_to_check} after clear, but got {get_response.status_code}. Response: {get_response.text}"

            search_payload = {"query_text": "any query", "top_k": 1, "filter_tag": "any"}
            search_response_after_clear = client_with_qdrant_override.post(
                "/semantic_search_cosine", json=search_payload
            )
            assert search_response_after_clear.status_code == 200
            results_after_clear = search_response_after_clear.json()["results"]
            if initial_upserted_ids:
                original_ids_set = set(initial_upserted_ids)
                found_original_ids_after_clear = [
                    res["id"] for res in results_after_clear if res["id"] in original_ids_set
                ]
                assert (
                    len(found_original_ids_after_clear) == 0
                ), f"Found previously upserted IDs {found_original_ids_after_clear} in search results after clear."
            else:
                assert (
                    len(results_after_clear) == 0
                ), "Search after clear should return no results if collection was empty or just cleared."
        finally:
            app.dependency_overrides.pop(_generate_openai_embedding, None)
