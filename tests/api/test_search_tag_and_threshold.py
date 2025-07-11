import pytest
from fastapi.testclient import TestClient

# from app.services.qdrant_service import QdrantService
# from app.models.search_models import SearchRequest, SearchResult

# Mock embedding function
# async def mock_embedding_function(text: str, model: str = "text-embedding-ada-002"):
#     vector = [0.0, 0.0, 0.0]
#     if "astronomy" in text:
#         vector = [0.1, 0.2, 0.8]  # Corresponds to "science"
#     elif "recipe" in text:
#         vector = [0.8, 0.1, 0.1]  # Corresponds to "cooking"
#     elif "ancient" in text:
#         vector = [0.2, 0.8, 0.1]  # Corresponds to "history"
#     return {"embedding": vector, "model": model, "text": text}

# class MockQdrantOperations:
#     def __init__(self):
#         self.points = {}
#         self.collection_name = "test_collection"

#     def upsert_vector(self, point_id: any, vector: list[float], metadata: dict, collection_name: str = "test_collection") -> bool:
#         self.points[point_id] = PointStruct(id=point_id, vector=vector, payload=metadata)
#         return True

#     def search_vector(self, query_vector: list[float], top_k: int = 5, filter_tag: str = None, score_threshold: float | None = None, collection_name: str = "test_collection"):
#         results = []
#
#         candidate_points = list(self.points.values())

#         for point in candidate_points:
#             score = 0.0
#             if query_vector == [0.1, 0.2, 0.8]:
#                 if point.id == 9001: score = 0.9
#                 elif point.id == 9002: score = 0.3
#                 elif point.id == 9003: score = 0.4
#
#             passes_filter = True
#             if filter_tag:
#                 if point.payload.get("tag") != filter_tag:
#                     passes_filter = False
#
#             passes_threshold = True
#             if score_threshold is not None and score < score_threshold:
#                 passes_threshold = False

#             if passes_filter and passes_threshold and score > 0:
#                  results.append(ScoredPoint(id=point.id, version=0, score=score, payload=point.payload, vector=point.vector))
#
#         results.sort(key=lambda p: p.score, reverse=True)
#         return results[:top_k]

#     def _ensure_collection(self):
#         pass

#     def __init__(self):
#         self.points = {}
#         self.collection_name = "test_collection"
#         self._ensure_collection()


# @pytest.fixture
# def client_with_qdrant_override(monkeypatch):
#     mock_qdrant_operations = MockQdrantOperations()

#     points_to_add = [
#         (9001, [0.1, 0.2, 0.8], {"text": "modern astronomy discoveries", "tag": "science"}),
#         (9002, [0.8, 0.1, 0.1], {"text": "new chicken recipe", "tag": "cooking"}),
#         (9003, [0.2, 0.8, 0.1], {"text": "ancient rome history", "tag": "history"}),
#     ]

#     for p_id, p_vector, p_payload in points_to_add:
#         mock_qdrant_operations.points[p_id] = PointStruct(id=p_id, vector=p_vector, payload=p_payload)

#     def override_get_qdrant_store():
#         return mock_qdrant_operations

#     monkeypatch.setattr(api_vector_search, "_generate_openai_embedding", mock_embedding_function)

#     app.dependency_overrides[get_qdrant_store] = override_get_qdrant_store

#     with TestClient(app) as client:
#         yield client

#     app.dependency_overrides.clear()
#     monkeypatch.undo()


@pytest.mark.unit
def test_search_with_tag_and_threshold(client_with_qdrant_override: TestClient):
    payload = {
        "query_text": "modern astronomy discoveries",
        "top_k": 5,
        "filter_tag": "science",
        "score_threshold": 0.8,
    }
    response = client_with_qdrant_override.post("/semantic_search_cosine/", json=payload)
    assert response.status_code == 200, response.text
    response_data = response.json()

    assert "results" in response_data
    results_list = response_data["results"]
    assert len(results_list) == 4
    # Check if the top result is indeed point 9001 or one of the expected science items
    # This part of the test might need adjustment based on actual scoring with the mock.
    result = results_list[0]
    assert result["payload"]["tag"] == "science"
    assert result["score"] >= 0.8
    assert result["id"] == 9001
