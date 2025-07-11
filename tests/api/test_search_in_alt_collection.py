import pytest
from fastapi.testclient import TestClient
from tests.mocks.qdrant_multi_collection import FakeQdrantClient
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from agent_data.vector_store.qdrant_store import QdrantStore


@pytest.fixture
def configured_qdrant_mock_for_alt_collection(monkeypatch, client_with_qdrant_override):
    # This fixture depends on client_with_qdrant_override to ensure general setup (env vars, app overrides) happens.
    # However, we will re-patch the QdrantClient specifically for this test's needs.

    # 1. Instantiate the multi-collection mock with dummy URL/key
    multi_collection_client = FakeQdrantClient(url="http://dummy-multi-collection-url:6333", api_key="dummy-multi-key")

    # 2. Clear any pre-existing data from this instance
    multi_collection_client.clear_all_data()

    # 3. Create and populate "alt_collection"
    multi_collection_client.create_collection(
        "alt_collection", vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
    )
    query_text = "alternate query"
    base_val = len(query_text) + ord(query_text[0])
    embedding_val = (base_val % 100) / 100.0
    mock_vector = [embedding_val] * 10 + [0.0] * (1536 - 10)
    points_to_upsert_alt = [
        PointStruct(id=2001, vector=mock_vector, payload={"original_text": "alternate query", "tag": "science"})
    ]
    multi_collection_client.upsert_points(collection_name="alt_collection", points=points_to_upsert_alt)

    # 4. Ensure the default "test_collection" (used by client_with_qdrant_override's seeding) also exists in this client
    # and seed it with standard data, as QdrantStore might expect it or other API calls in the test.
    # The QDRANT_COLLECTION_NAME is "test_collection" in client_with_qdrant_override.
    default_test_collection_name = "test_collection"
    if not multi_collection_client.collection_exists(default_test_collection_name):
        multi_collection_client.create_collection(
            default_test_collection_name, vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
    # Re-seed standard points if necessary, client_with_qdrant_override might have done this already
    # but to the basic FakeQdrantClient. We need them in *our* multi_collection_client for other tests if they run
    # in a context where this patch is active. For this single test, "alt_collection" is key.
    # For simplicity, we'll assume test_search_in_alt_collection only cares about alt_collection for its primary assertion.

    # 5. Make QdrantStore use this specific multi_collection_client instance
    def mock_qdrant_client_constructor(*args, **kwargs):
        # print(f"DEBUG: mock_qdrant_client_constructor returning multi_collection_client for {args} {kwargs}")
        return multi_collection_client

    # This is the crucial part: patch where QdrantStore gets its QdrantClient
    monkeypatch.setattr("agent_data.vector_store.qdrant_store.QdrantClient", mock_qdrant_client_constructor)

    # 6. Reset QdrantStore singleton so it re-initializes with the newly patched client
    if hasattr(QdrantStore, "_instance"):
        QdrantStore._instance = None
    if hasattr(QdrantStore, "_initialized"):  # Ensure re-initialization logic in QdrantStore is triggered
        QdrantStore._initialized = False

    # The QdrantStore instance obtained via app.dependency_overrides[get_qdrant_store]()
    # inside client_with_qdrant_override should now use our multi_collection_client.
    # We don't need to yield the client itself if the test uses client_with_qdrant_override for API calls.
    # The effect is through the monkeypatch.


@pytest.mark.unit
def test_search_in_alt_collection(configured_qdrant_mock_for_alt_collection, client_with_qdrant_override: TestClient):
    # client_with_qdrant_override is the TestClient.
    # Its underlying QdrantStore should now be using the multi-collection mock client
    # configured by configured_qdrant_mock_for_alt_collection.

    response = client_with_qdrant_override.post(
        "/semantic_search_cosine",
        json={
            "query_text": "alternate query",  # Embedding will match point 2001
            "filter_tag": "science",  # Payload tag will match
            "top_k": 1,
            "score_threshold": 0.5,  # Similarity will be 1.0, so this passes
            "collection_name": "alt_collection",
        },
    )
    # print(f"DEBUG: API Response: {response.status_code}, {response.text}") # For debugging
    assert response.status_code == 200
    results = response.json().get("results", [])
    assert (
        len(results) == 1
    ), f"Expected 1 result for 'alternate query', got {len(results)}. Response: {response.json()}"
    assert (
        results[0]["id"] == "2001"
    ), f"Expected ID '2001' (str) for 'alternate query'. Got: {results[0]['id'] if results else 'No results'}"
