from typing import List, Optional, Dict, Any
import numpy as np
from qdrant_client.http.models import PointStruct, UpdateResult, VectorParams, Distance, Record, ScoredPoint

VECTOR_DIMENSION = 1536


def _pad_vector(vector: List[float], target_dimension: int) -> List[float]:
    current_dimension = len(vector)
    if current_dimension >= target_dimension:
        return vector[:target_dimension]
    return vector + [0.0] * (target_dimension - current_dimension)


class FakeQdrantClient:
    _collections: Dict[str, Dict[str, Any]] = {}

    def __init__(self, url: str, api_key: Optional[str] = None, **kwargs):
        pass

    def clear_all_data(self):
        self._collections = {}

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self._collections

    def create_collection(self, collection_name: str, vectors_config: Any, **kwargs):
        # Ensure vectors_config is treated as VectorParams or similar, access size via attribute
        if isinstance(vectors_config, VectorParams):
            size = vectors_config.size
            distance = vectors_config.distance
        elif isinstance(vectors_config, dict):  # Fallback for older qdrant_client versions or dict-based config
            size = vectors_config.get("size", VECTOR_DIMENSION)
            distance = vectors_config.get("distance", Distance.COSINE)
        else:  # Default if type is unknown
            size = VECTOR_DIMENSION
            distance = Distance.COSINE

        self._collections[collection_name] = {
            "config": {"params": {"vectors": {"size": size, "distance": distance}}},
            "points": {},
        }

    def upsert_points(self, collection_name: str, points: List[PointStruct], **kwargs):
        if collection_name not in self._collections:
            # If collection does not exist, create it with default VectorParams
            self.create_collection(collection_name, VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE))

        collection_points = self._collections[collection_name]["points"]
        for point in points:
            point_id = str(point.id)

            # Ensure vector is not None before padding
            vector_to_pad = point.vector if point.vector is not None else []

            processed_payload = {}
            if point.payload:
                for k, v in point.payload.items():
                    if isinstance(v, str):
                        processed_payload[k] = v.lower()
                    elif (
                        isinstance(v, dict) and "type" in v and v["type"] == "keyword"
                    ):  # Handle specific dict format for tags
                        processed_payload[k] = v["value"].lower()
                    else:
                        processed_payload[k] = v

            collection_points[point_id] = {
                "vector": _pad_vector(vector_to_pad, VECTOR_DIMENSION),
                "payload": processed_payload,
            }
        return UpdateResult(operation_id=1, status="completed")

    def search_points(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        query_filter: Optional[Dict] = None,
        score_threshold: Optional[float] = None,
        **kwargs
    ) -> List[ScoredPoint]:
        self._ensure_collection_exists(collection_name)

        points = []
        collection_points = self._collections[collection_name]["points"]

        for point_id_iterator, point_data in collection_points.items():
            # Basic filtering by tag
            if query_filter and "must" in query_filter:
                match = False
                for condition in query_filter["must"]:
                    if "key" in condition and "match" in condition and "value" in condition["match"]:
                        if point_data["payload"].get(condition["key"]) == condition["match"]["value"]:
                            match = True
                            break
                if not match:
                    continue

            # Cosine similarity calculation
            vec_a = np.array(query_vector)
            vec_b = np.array(point_data["vector"])
            cosine_sim = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))

            # Apply score_threshold if provided
            if score_threshold is not None and cosine_sim < score_threshold:
                continue

            # Create ScoredPoint with a placeholder version and the calculated score
            points.append(
                ScoredPoint(
                    id=point_id_iterator,
                    version=1,  # Placeholder version for mock
                    score=float(cosine_sim.item()),
                    payload=point_data["payload"],
                    vector=point_data["vector"],
                )
            )

        # Sort by score descending
        points.sort(key=lambda p: p.score, reverse=True)
        return points[:limit]

    def retrieve(self, collection_name: str, ids: List[Any], **kwargs) -> List[ScoredPoint]:
        self._ensure_collection_exists(collection_name)

        retrieved_points: List[ScoredPoint] = []
        collection_points = self._collections[collection_name]["points"]

        for point_id_param in ids:
            str_point_id = str(point_id_param)
            if str_point_id in collection_points:
                point_data = collection_points[str_point_id]
                # Create ScoredPoint with placeholder version and score
                retrieved_points.append(
                    ScoredPoint(
                        id=str_point_id,
                        version=1,  # Placeholder for mock
                        score=1.0,  # Placeholder score for retrieve, as it's not calculated
                        payload=point_data["payload"],
                        vector=point_data["vector"],
                    )
                )
        return retrieved_points

    def _ensure_collection_exists(self, collection_name: str):
        """Helper to ensure a collection exists, creating it if not."""
        if not self.collection_exists(collection_name):
            # Create with default settings if accessed before explicit creation
            # This mimics some behaviors of a real Qdrant client that might auto-create
            # or assume existence based on operations.
            self.create_collection(collection_name, VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE))
            # logger.info(f"Mock collection '{collection_name}' auto-created.") # Optional logging

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Optional[Any] = None,
        limit: int = 10,
        offset: Optional[Any] = None,
        **kwargs
    ) -> tuple[list[Record], Any]:
        self._ensure_collection_exists(collection_name)

        all_points = list(self._collections[collection_name]["points"].items())

        # Apply filtering if scroll_filter is provided
        # This is a simplified filter handling, adapt as needed for complex filters
        filtered_points_data = []
        if scroll_filter and hasattr(scroll_filter, "must"):
            for point_id, point_data in all_points:
                match = True
                for condition in scroll_filter.must:
                    field_name = condition.key
                    # Assuming simple exact match for now
                    if hasattr(condition, "match") and hasattr(condition.match, "value"):
                        expected_value = condition.match.value.lower()
                        payload_value = point_data["payload"].get(field_name)
                        if not (payload_value and str(payload_value).lower() == expected_value):
                            match = False
                            break
                    # Extend with other filter condition types as needed
                if match:
                    filtered_points_data.append((point_id, point_data))
        else:  # No filter, use all points
            for point_id, point_data in all_points:
                filtered_points_data.append((point_id, point_data))

        # Apply offset and limit
        start_index = 0
        if offset:  # Assuming offset is an index or a point_id to start after
            try:  # If offset is an int, use as index
                start_index = int(offset)
            except ValueError:  # If offset is a point_id, find its index
                for i, (pid, _) in enumerate(filtered_points_data):
                    if pid == offset:
                        start_index = i + 1
                        break

        end_index = start_index + limit
        paginated_points_data = filtered_points_data[start_index:end_index]

        records = []
        for point_id, point_data in paginated_points_data:
            # Convert point_id back to its original type if necessary
            try:
                id_val = int(point_id)
            except ValueError:
                id_val = point_id
            records.append(
                Record(
                    id=id_val,
                    payload=point_data["payload"],
                    vector=point_data["vector"],
                    # shard_key is optional and not included here
                )
            )

        # Determine next_page_offset
        # If there are more points after the current page, the offset for the next page is the ID of the last point retrieved
        # Or, if using integer offsets, it would be end_index. For simplicity with IDs, this can be complex.
        # A simpler approach for mock: if end_index < len(filtered_points_data), next_page_offset = end_index (as int) or filtered_points_data[end_index][0] (as ID)
        next_page_offset = None
        if end_index < len(filtered_points_data):
            next_page_offset = filtered_points_data[end_index][0]  # Using point ID as offset for next page

        return records, next_page_offset

    # Add a search method for compatibility with QdrantStore, which calls search_points
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        query_filter: Optional[Dict] = None,
        score_threshold: Optional[float] = None,
        **kwargs
    ) -> List[ScoredPoint]:
        # QdrantStore might pass other kwargs, ensure search_points can handle or ignore them if not used by the mock.
        # Currently, search_points also accepts **kwargs, so this should be fine.
        return self.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter,
            score_threshold=score_threshold,
            **kwargs
        )

    # Add create_payload_index for compatibility with QdrantStore
    def create_payload_index(self, collection_name: str, field_name: str, field_schema: Any, **kwargs):
        # This is a mock, so we don't actually need to create an index.
        # We can just log that it was called if needed for debugging.
        # print(f"Mock: create_payload_index called for collection '{collection_name}', field '{field_name}'")
        pass  # No-op for the mock
