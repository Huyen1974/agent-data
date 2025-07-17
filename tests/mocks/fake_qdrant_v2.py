"""FakeQdrant V2 - Mock implementation for VectorStore interface testing."""

import logging
from typing import Any

import numpy as np
from qdrant_client.http import models
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    PointStruct,
    VectorParams,
)

logger = logging.getLogger(__name__)


class FakeQdrantV2:
    """Mock Qdrant client for VectorStore interface testing."""

    # Shared data across all instances (simulating Qdrant Cloud)
    _shared_data = {}
    _collection_configs = {}

    def __init__(self, url: str, api_key: str, timeout: float = 30.0):
        """Initialize the fake Qdrant client."""
        self.url = url
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def clear_all_data(cls):
        """Clear all shared data."""
        cls._shared_data.clear()
        cls._collection_configs.clear()

    def get_collections(self):
        """Get list of collections."""
        collections = []
        for name in self._collection_configs.keys():
            collections.append(type("CollectionDescription", (), {"name": name})())
        return type("CollectionsResponse", (), {"collections": collections})()

    def create_collection(self, collection_name: str, vectors_config: VectorParams):
        """Create a new collection."""
        if collection_name not in self._shared_data:
            self._shared_data[collection_name] = {}
            self._collection_configs[collection_name] = {
                "vector_size": vectors_config.size,
                "distance": vectors_config.distance,
            }
        return True

    def get_collection(self, collection_name: str):
        """Get collection info."""
        if collection_name not in self._shared_data:
            raise ValueError(f"Collection {collection_name} does not exist")

        config = self._collection_configs.get(collection_name, {})
        vectors_count = len(self._shared_data[collection_name])

        return type(
            "CollectionInfo", (), {"vectors_count": vectors_count, "config": config}
        )()

    def upsert(self, collection_name: str, points: list[PointStruct]):
        """Upsert points into collection."""
        if collection_name not in self._shared_data:
            self._shared_data[collection_name] = {}

        for point in points:
            self._shared_data[collection_name][str(point.id)] = {
                "id": point.id,
                "vector": point.vector,
                "payload": point.payload or {},
            }

        return type(
            "UpdateResult",
            (),
            {"operation_id": "fake-operation-id", "status": "completed"},
        )()

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        query_filter: Filter | None = None,
        limit: int = 10,
        score_threshold: float = 0.0,
    ):
        """Search for similar vectors."""
        if collection_name not in self._shared_data:
            return []

        data = self._shared_data[collection_name]
        results = []

        for point_id, point_data in data.items():
            # Apply filter if provided
            if query_filter:
                if not self._matches_filter(point_data["payload"], query_filter):
                    continue

            # Calculate cosine similarity
            similarity = self._calculate_similarity(query_vector, point_data["vector"])

            # Apply threshold
            if similarity < score_threshold:
                continue

            results.append(
                type(
                    "ScoredPoint",
                    (),
                    {
                        "id": point_data["id"],
                        "score": similarity,
                        "payload": point_data["payload"],
                        "vector": point_data["vector"],
                    },
                )()
            )

        # Sort by score (descending) and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Filter | None = None,
        limit: int = 10,
    ):
        """Scroll through points in collection."""
        if collection_name not in self._shared_data:
            return ([], None)

        data = self._shared_data[collection_name]
        results = []

        for point_id, point_data in data.items():
            # Apply filter if provided
            if scroll_filter:
                if not self._matches_filter(point_data["payload"], scroll_filter):
                    continue

            results.append(
                type(
                    "Record",
                    (),
                    {
                        "id": point_data["id"],
                        "payload": point_data["payload"],
                        "vector": point_data["vector"],
                    },
                )()
            )

            if len(results) >= limit:
                break

        return (results, None)  # (points, next_page_offset)

    def delete(self, collection_name: str, points_selector):
        """Delete points from collection."""
        if collection_name not in self._shared_data:
            return type(
                "UpdateResult",
                (),
                {"operation_id": "fake-operation-id", "status": "completed"},
            )()

        data = self._shared_data[collection_name]
        deleted_count = 0

        if hasattr(points_selector, "filter"):
            # FilterSelector - delete by filter
            filter_obj = points_selector.filter
            points_to_delete = []

            for point_id, point_data in data.items():
                if self._matches_filter(point_data["payload"], filter_obj):
                    points_to_delete.append(point_id)

            for point_id in points_to_delete:
                del data[point_id]
                deleted_count += 1

        return type(
            "UpdateResult",
            (),
            {
                "operation_id": "fake-operation-id",
                "status": "completed",
                "deleted_count": deleted_count,
            },
        )()

    def close(self):
        """Close the connection (no-op for mock)."""
        pass

    def _matches_filter(self, payload: dict[str, Any], filter_obj: Filter) -> bool:
        """Check if payload matches the filter."""
        if not filter_obj or not hasattr(filter_obj, "must"):
            return True

        if not filter_obj.must:
            return True

        for condition in filter_obj.must:
            if hasattr(condition, "key") and hasattr(condition, "match"):
                key = condition.key
                match_value = (
                    condition.match.value
                    if hasattr(condition.match, "value")
                    else condition.match
                )

                if key not in payload:
                    return False

                if payload[key] != match_value:
                    return False

        return True

    def _calculate_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Convert to numpy arrays for calculation
            a = np.array(vec1, dtype=float)
            b = np.array(vec2, dtype=float)

            # Handle zero vectors
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)

            if norm_a == 0 or norm_b == 0:
                return 0.0

            # Cosine similarity
            similarity = np.dot(a, b) / (norm_a * norm_b)
            return float(similarity)
        except Exception:
            # Fallback to simple similarity
            return 0.5


# Create the mock fixture
class MockQdrantStore:
    """Mock QdrantStore for testing VectorStore interface."""

    def __init__(self):
        self.client = FakeQdrantV2("http://dummy:6333", "dummy-key")
        self.collection_name = "test_collection"
        self.vector_size = 1536
        self.distance = Distance.COSINE
        self._collection_initialized = False

    async def _ensure_collection(self):
        """Ensure collection exists."""
        if not self._collection_initialized:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=self.distance
                ),
            )
            self._collection_initialized = True

    async def upsert_vector(
        self,
        vector_id: str,
        vector: list[float] | np.ndarray,
        metadata: dict[str, Any] | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        """Upsert a vector."""
        await self._ensure_collection()

        if isinstance(vector, np.ndarray):
            vector = vector.tolist()

        payload = metadata.copy() if metadata else {}
        if tag:
            payload["tag"] = tag

        point = PointStruct(id=vector_id, vector=vector, payload=payload)
        self.client.upsert(self.collection_name, [point])

        return {"success": True, "vector_id": vector_id}

    async def query_vectors_by_tag(
        self,
        tag: str,
        query_vector: list[float] | np.ndarray | None = None,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Query vectors by tag."""
        await self._ensure_collection()

        tag_filter = Filter(
            must=[FieldCondition(key="tag", match=models.MatchValue(value=tag))]
        )

        if query_vector is not None:
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()

            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=tag_filter,
                limit=limit,
                score_threshold=threshold,
            )
        else:
            results, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=tag_filter,
                limit=limit,
            )
            # Convert to search-like format
            search_results = []
            for point in results:
                search_results.append(
                    type(
                        "ScoredPoint",
                        (),
                        {
                            "id": point.id,
                            "score": 1.0,
                            "payload": point.payload,
                            "vector": point.vector,
                        },
                    )()
                )
            results = search_results

        formatted_results = []
        for point in results:
            formatted_results.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "metadata": point.payload,
                    "vector": point.vector,
                }
            )

        return formatted_results

    async def delete_vectors_by_tag(self, tag: str) -> dict[str, Any]:
        """Delete vectors by tag."""
        await self._ensure_collection()

        delete_filter = Filter(
            must=[FieldCondition(key="tag", match=models.MatchValue(value=tag))]
        )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(filter=delete_filter),
        )

        return {"success": True, "tag": tag}

    async def get_vector_count(self) -> int:
        """Get vector count."""
        await self._ensure_collection()
        info = self.client.get_collection(self.collection_name)
        return info.vectors_count

    async def health_check(self) -> bool:
        """Health check."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
