import logging
import random
import uuid
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable, Sequence, Mapping, Tuple, Annotated

import numpy as np

try:
    from pydantic import Strict
except ImportError:
    # Mock Strict for type annotation purposes
    def Strict(strict=True):
        return None


from qdrant_client.http.models import (
    PointStruct,
    UpdateResult,
    Filter,
    Distance,
    ScoredPoint,
    Record,
    PointsSelector,
    VectorParams,
    CollectionInfo,
    CollectionsResponse,
    CollectionDescription,
    CountResult,
    PayloadSelectorInclude,
    PayloadSelectorExclude,
    ReadConsistencyType,
    WriteOrdering,
    HnswConfigDiff,
    OptimizersConfigDiff,
    WalConfigDiff,
    ScalarQuantization,
    ProductQuantization,
    BinaryQuantization,
    InitFrom,
    StrictModeConfig,
    PayloadSchemaType,
    KeywordIndexParams,
    IntegerIndexParams,
    FloatIndexParams,
    GeoIndexParams,
    TextIndexParams,
    BoolIndexParams,
    DatetimeIndexParams,
    UuidIndexParams,
    SearchParams,
    NamedVector,
    NamedSparseVector,
    OrderBy,
    Batch,
    FilterSelector,
    PointIdsList,
    SparseVectorParams,
    ShardingMethod,
)

try:
    from qdrant_client.grpc import collections_pb2, points_pb2
except ImportError:
    collections_pb2 = None
    points_pb2 = None

# Configure logging for the mock if you want to see its internal logs,
# otherwise, it will use root logger settings if any.
# logging.basicConfig(level=logging.INFO) # Example: enable logging for this module
logger = logging.getLogger(__name__)

# Define a constant for vector dimension for clarity
VECTOR_DIMENSION = 1536

# Type alias for the (async) EmbeddingFunction
EmbeddingFunctionAsync = Callable[[List[str]], Awaitable[Dict[str, Any]]]


def _ensure_flat_float_list(vec: Any) -> List[float]:
    """Ensures the input is a flat list of floats."""
    if isinstance(vec, np.ndarray):
        vec = vec.tolist()  # Convert numpy array to list

    if not isinstance(vec, list):
        # If it's a single number or something else not iterable, this won't work well.
        # Assuming it should be some form of list-like structure if not a list.
        # This case should ideally not be hit if type hints are followed upstream.
        try:
            vec = list(vec)
        except TypeError:
            raise ValueError(f"Input vector {vec} cannot be converted to a list.")

    flat_list = []
    for item in vec:
        if isinstance(item, (list, tuple, np.ndarray)):
            # If an item is itself a list/tuple/array, extend (flatten one level)
            if isinstance(item, np.ndarray):
                item = item.tolist()
            for sub_item in item:
                try:
                    flat_list.append(float(sub_item))
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Cannot convert sub-item '{sub_item}' to float: {e}")
        else:
            try:
                flat_list.append(float(item))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Cannot convert item '{item}' to float: {e}")
    return flat_list


def _pad_vector(vector: Any, target_dimension: int = VECTOR_DIMENSION) -> List[float]:
    """Pads or truncates a vector to the target dimension. Ensures input is processed as a flat list of floats."""
    try:
        flat_vector = _ensure_flat_float_list(vector)
    except ValueError:
        # print(f"_pad_vector error during _ensure_flat_float_list: {e}. Original vector: {vector}")
        raise  # Re-raise the error to make it visible

    if not flat_vector:  # Handle None or empty list vector after flattening
        return [0.0] * target_dimension

    current_dimension = len(flat_vector)
    if current_dimension == target_dimension:
        return flat_vector
    elif current_dimension < target_dimension:
        return flat_vector + [0.0] * (target_dimension - current_dimension)
    else:  # current_dimension > target_dimension
        return flat_vector[:target_dimension]


# Predefined vectors for specific texts, padded to VECTOR_DIMENSION
# These are used by mock_embedding_function_for_conftest
PREDEFINED_VECTORS_FOR_EMBEDDING = {
    # Vector for point 9001 in conftest.py is [0.1, 0.2, 0.8, 0.0, ..., 0.0]
    "modern astronomy discoveries": _pad_vector([0.1, 0.2, 0.8]),  # This will pad with 0.0s
    "history of ancient egypt": _pad_vector([0.3, 0.2, 0.1] + [0.02] * (VECTOR_DIMENSION - 3)),
    "delicious pasta recipes": _pad_vector([0.1, 0.5, 0.2] + [0.03] * (VECTOR_DIMENSION - 3)),
    "future of ai in politics": _pad_vector([0.6, 0.1, 0.3] + [0.04] * (VECTOR_DIMENSION - 3)),
    # Add other specific texts if tests rely on them
    "This is a test document for ensuring non-ASCII characters are handled: 東京 and emojis 😊": _pad_vector(
        [0.1] * 10
    ),
    "Another test document for semantic search": _pad_vector([0.2] * 10),
    "A document about apples and oranges": _pad_vector([0.3] * 10),
    "Document for threshold test": _pad_vector([0.4] * 10),
    "Another test document": _pad_vector([0.5] * 10),
    " சென்னை ": _pad_vector([0.6] * 10),
    "你好世界": _pad_vector([0.7] * 10),
    "deep space exploration": _pad_vector([0.1, 0.2, 0.7] + [0.0] * (VECTOR_DIMENSION - 3)),  # Added for CLI82B
    "Sample text for point 9001": _pad_vector(
        [0.1, 0.2, 0.8] + [0.0] * (VECTOR_DIMENSION - 3)
    ),  # Match conftest seeding
    "Sample text for point 1001": _pad_vector([0.1, 0.2, 0.7] + [0.0] * (VECTOR_DIMENSION - 3)),
    "Sample text for point 1002": _pad_vector([0.1, 0.2, 0.6] + [0.0] * (VECTOR_DIMENSION - 3)),
    "Sample text for point 1003": _pad_vector([0.1, 0.2, 0.5] + [0.0] * (VECTOR_DIMENSION - 3)),
}


async def mock_embedding_function_for_conftest(
    texts: Union[str, List[str]], model: str = "text-embedding-ada-002"
) -> Dict[str, Any]:
    """
    Mock async embedding function that returns predefined 1536-dimension vectors for specific inputs,
    otherwise generates simple deterministic vectors padded to 1536 dimensions.
    Output matches the structure of OpenAI's embedding response.
    This version is for use in conftest.py.
    """
    input_texts: List[str]
    if isinstance(texts, str):
        input_texts = [texts]
    else:
        input_texts = texts

    embeddings = []
    for i, text_input in enumerate(input_texts):
        # Normalize text input for matching keys in PREDEFINED_VECTORS_FOR_EMBEDDING
        normalized_text = text_input.lower().strip()
        found_predefined = False
        for key_text, vec in PREDEFINED_VECTORS_FOR_EMBEDDING.items():
            if key_text in normalized_text:  # More flexible matching
                embeddings.append(vec)
                found_predefined = True
                break
        if not found_predefined:
            # Simple deterministic vector based on text length and index, then padded
            base_val = float(len(text_input) % 100 + i + 1) / 100.0  # Keep values small
            raw_vector = [base_val] * min(10, VECTOR_DIMENSION)  # Keep raw simple
            embeddings.append(_pad_vector(raw_vector, VECTOR_DIMENSION))

    return {
        "embedding": embeddings,  # List of vectors
        "model": model,
        "usage": {"prompt_tokens": sum(len(t) for t in texts), "total_tokens": sum(len(t) for t in texts)},
    }


class FakeQdrantClient:
    _collections: Dict[str, Dict[str, Any]] = {}  # Class variable to store all collections and their data
    # Structure: {"collection_name": {"points": {id: {"vector": [], "payload": {}}}, "config": {}, "indexed_fields": set()}}

    def __init__(self, url: str, api_key: Optional[str] = None, timeout: int = 10, **kwargs):
        """
        Constructor to mimic the real QdrantClient, compatible with conftest.py.
        url, api_key, timeout are part of the signature but largely unused by the mock itself,
        as it operates on an in-memory class-level dictionary.
        """
        self.url = url
        self.api_key = api_key
        self.timeout = timeout
        # Other kwargs are ignored for this mock.
        # print(f"FakeQdrantClient initialized with url: {url}, api_key: {'set' if api_key else 'not set'}")

    @classmethod
    def clear_all_data(cls):
        """Clears all collections and their data. Called by conftest.py."""
        # print(f"FakeQdrantClient.clear_all_data: Clearing all collections. Before: {list(cls._collections.keys())}")
        cls._collections.clear()
        # print("FakeQdrantClient.clear_all_data: All data cleared.")

    def close(self, grpc_grace: Optional[float] = None, **kwargs: Any) -> None:
        """No-op, mimics real client."""
        # print("FakeQdrantClient: close() called.")
        pass

    def collection_exists(self, collection_name: str, **kwargs: Any) -> bool:
        """Checks if a collection exists."""
        exists = collection_name in self._collections
        # print(f"FakeQdrantClient.collection_exists: Collection '{collection_name}' exists? {exists}")
        return exists

    def create_collection(
        self,
        collection_name: str,
        vectors_config: Union[VectorParams, Mapping[str, VectorParams], None] = None,
        sparse_vectors_config: Optional[Mapping[str, SparseVectorParams]] = None,
        shard_number: Optional[int] = None,
        sharding_method: Optional[ShardingMethod] = None,
        replication_factor: Optional[int] = None,
        write_consistency_factor: Optional[int] = None,
        on_disk_payload: Optional[bool] = None,
        hnsw_config: Union[HnswConfigDiff, "collections_pb2.HnswConfigDiff", None] = None,
        optimizers_config: Union[OptimizersConfigDiff, "collections_pb2.OptimizersConfigDiff", None] = None,
        wal_config: Union[WalConfigDiff, "collections_pb2.WalConfigDiff", None] = None,
        quantization_config: Union[
            ScalarQuantization, ProductQuantization, BinaryQuantization, "collections_pb2.QuantizationConfig", None
        ] = None,
        init_from: Union[InitFrom, str, None] = None,
        timeout: Optional[int] = None,
        strict_mode_config: Optional[StrictModeConfig] = None,
        **kwargs: Any,
    ) -> bool:
        """Creates a new collection."""
        if collection_name in self._collections:
            # print(f"FakeQdrantClient.create_collection: Collection '{collection_name}' already exists. Not recreating.")
            return False  # Qdrant might error or return False if exists

        vector_size = VECTOR_DIMENSION  # Default
        distance = Distance.COSINE  # Default
        if isinstance(vectors_config, dict):
            vector_size = vectors_config.get("size", VECTOR_DIMENSION)
            distance = vectors_config.get("distance", Distance.COSINE)
        elif isinstance(vectors_config, VectorParams):
            vector_size = vectors_config.size
            distance = vectors_config.distance

        self._collections[collection_name] = {
            "points": {},
            "config": {"params": {"vectors": {"size": vector_size, "distance": distance}}},
            "indexed_fields": set(),
        }
        # print(f"FakeQdrantClient.create_collection: Collection '{collection_name}' created with vector_size={vector_size}, distance={distance}.")
        return True

    def delete_collection(self, collection_name: str, timeout: Optional[int] = None, **kwargs: Any) -> bool:
        """Deletes a collection."""
        if collection_name in self._collections:
            del self._collections[collection_name]
            # print(f"FakeQdrantClient.delete_collection: Collection '{collection_name}' deleted.")
            return True
        # print(f"FakeQdrantClient.delete_collection: Collection '{collection_name}' not found for deletion.")
        return False

    def get_collection(self, collection_name: str, **kwargs: Any) -> CollectionInfo:
        """Gets information about a collection."""
        if collection_name not in self._collections:
            raise ValueError(f"Collection {collection_name} not found")  # Mimic Qdrant error

        config = self._collections[collection_name].get("config", {})
        params = config.get("params", {})

        # Make up some stats for CollectionInfo
        status = "green"
        optimizer_status = "ok"
        vectors_count = len(self._collections[collection_name].get("points", {}))
        segments_count = 1  # Mock value
        disk_data_size = vectors_count * VECTOR_DIMENSION * 4  # Rough estimate in bytes
        ram_data_size = vectors_count * VECTOR_DIMENSION * 4  # Rough estimate in bytes
        payload_schema = {}  # TODO: Could inspect payloads to build this if needed

        collection_info = CollectionInfo(
            status=status,
            optimizer_status=optimizer_status,
            vectors_count=vectors_count,
            segments_count=segments_count,
            disk_data_size=disk_data_size,
            ram_data_size=ram_data_size,
            payload_schema=payload_schema,
            params=params,  # This should contain the vectors_config
            # config=config, # The API uses params for config details
        )
        # print(f"FakeQdrantClient.get_collection: Info for '{collection_name}': {collection_info}")
        return collection_info

    # Alias for qdrant_client v1.1.1+ compatibility if QdrantStore uses client.upsert(...)
    def upsert(
        self,
        collection_name: str,
        points: Union[Batch, "Sequence[Union[PointStruct, points_pb2.PointStruct]]"],
        wait: bool = True,
        ordering: Optional[WriteOrdering] = None,
        shard_key_selector: Union[
            "Annotated[int, Strict(strict=True)]",
            "Annotated[str, Strict(strict=True)]",
            "List[Union[Annotated[int, Strict(strict=True)], Annotated[str, Strict(strict=True)]]]",
            None,
        ] = None,
        **kwargs: Any,
    ) -> UpdateResult:
        # Inline upsert logic (simplified version)
        if not self.collection_exists(collection_name):
            self.create_collection(collection_name, VectorParams(size=VECTOR_DIMENSION, distance=Distance.COSINE))

        collection_data = self._collections[collection_name]
        target_dimension = (
            collection_data.get("config", {}).get("params", {}).get("vectors", {}).get("size", VECTOR_DIMENSION)
        )

        updated_ids = []
        for point in points:
            if not isinstance(point.id, (int, str, uuid.UUID)):
                raise TypeError(f"Point ID must be int, str, or UUID, got {type(point.id)}")

            padded_vector = None
            if point.vector is not None:
                if isinstance(point.vector, dict):
                    padded_vector = {}
                    for name, vec_data in point.vector.items():
                        padded_vector[name] = _pad_vector(list(vec_data), target_dimension)
                else:
                    padded_vector = _pad_vector(list(point.vector), target_dimension)

            processed_payload = {}
            if point.payload:
                for key, value in point.payload.items():
                    if key == "tag" and isinstance(value, str):
                        processed_payload[key] = value.lower()
                    elif key == "tags" and isinstance(value, list):
                        processed_payload[key] = sorted([str(t).lower() for t in value if isinstance(t, str)])
                    else:
                        processed_payload[key] = value

            collection_data["points"][point.id] = {"vector": padded_vector, "payload": processed_payload}
            updated_ids.append(point.id)

        return UpdateResult(operation_id=random.randint(1, 1000), status="completed")

    def list_collections(self, timeout: Optional[int] = None) -> CollectionsResponse:
        """Lists all collections."""
        collection_descriptions = [CollectionDescription(name=name) for name in self._collections.keys()]
        return CollectionsResponse(collections=collection_descriptions)

    def upsert_points(
        self, collection_name: str, points: List[PointStruct], wait: bool = True, **kwargs
    ) -> UpdateResult:
        """Alias for upsert method to maintain compatibility with tests"""
        return self.upsert(collection_name=collection_name, points=points, wait=wait, **kwargs)

    def retrieve(
        self,
        collection_name: str,
        ids: Sequence[Union[int, str, "points_pb2.PointId"]],
        with_payload: Union[
            bool, Sequence[str], PayloadSelectorInclude, PayloadSelectorExclude, "points_pb2.WithPayloadSelector"
        ] = True,
        with_vectors: Union[bool, Sequence[str]] = False,
        consistency: Union[int, ReadConsistencyType, None] = None,
        shard_key_selector: Union[int, str, List[Union[int, str]], None] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Record]:
        """Retrieves points by their IDs."""
        if not self.collection_exists(collection_name):
            # print(f"FakeQdrantClient.retrieve: Collection '{collection_name}' not found.")
            return []

        retrieved_records: List[Record] = []
        collection_points = self._collections[collection_name]["points"]

        for point_id in ids:
            # Handle potential type mismatches for point_id (e.g. str '123' vs int 123)
            point_data = None
            if point_id in collection_points:
                point_data = collection_points[point_id]
            elif isinstance(point_id, str) and point_id.isdigit() and int(point_id) in collection_points:
                point_data = collection_points[int(point_id)]
            elif isinstance(point_id, int) and str(point_id) in collection_points:
                point_data = collection_points[str(point_id)]

            if point_data:
                record = Record(
                    id=point_id,  # Use the requested ID type in the result
                    payload=point_data["payload"] if with_payload else None,
                    vector=point_data["vector"] if with_vectors else None,
                )
                retrieved_records.append(record)
        # print(f"FakeQdrantClient.retrieve: Retrieved {len(retrieved_records)} records from '{collection_name}'. IDs: {[r.id for r in retrieved_records]}")
        return retrieved_records

    def search(
        self,
        collection_name: str,
        query_vector: Union[
            Sequence[float],
            "tuple[str, list[float]]",
            NamedVector,
            NamedSparseVector,
            "np.ndarray",
        ],
        query_filter: Union[Filter, "points_pb2.Filter", None] = None,
        search_params: Union[SearchParams, "points_pb2.SearchParams", None] = None,
        limit: int = 10,
        offset: Optional[int] = None,
        with_payload: Union[
            bool, Sequence[str], PayloadSelectorInclude, PayloadSelectorExclude, "points_pb2.WithPayloadSelector"
        ] = True,
        with_vectors: Union[bool, Sequence[str]] = False,
        score_threshold: Optional[float] = None,
        append_payload: bool = True,
        consistency: Union["Annotated[int, Strict(strict=True)]", ReadConsistencyType, None] = None,
        shard_key_selector: Union[
            "Annotated[int, Strict(strict=True)]",
            "Annotated[str, Strict(strict=True)]",
            "List[Union[Annotated[int, Strict(strict=True)], Annotated[str, Strict(strict=True)]]]",
            None,
        ] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> List[ScoredPoint]:
        """Searches for points in a collection. Renamed from search_points."""
        # print(f"FakeQdrantClient.search: In '{collection_name}', limit {limit}, threshold {score_threshold}, filter: {query_filter is not None}")
        if not self.collection_exists(collection_name):
            # print(f"FakeQdrantClient.search: Collection '{collection_name}' not found.")
            return []

        collection_store = self._collections[collection_name]
        collection_points_data = collection_store["points"]
        collection_config = collection_store["config"]

        target_dimension = collection_config.get("params", {}).get("vectors", {}).get("size", VECTOR_DIMENSION)

        # Ensure query_vector is a flat list of floats before padding and converting to numpy
        # This is where the error occurred: np.array(_pad_vector(query_vector, target_dimension))
        try:
            flat_query_vector = _ensure_flat_float_list(query_vector)
            padded_query_list = _pad_vector(flat_query_vector, target_dimension)
            padded_query_vector_np = np.array(padded_query_list)
        except ValueError:
            # print(f"Error processing query_vector in FakeQdrantClient.search: {e}. Original query_vector: {query_vector}")
            # This might indicate that the mock_embedding_function is not returning a clean List[float]
            # or it's being wrapped in an extra list layer somewhere before this point.
            raise  # Re-raise to make test fail clearly with this error.

        results_with_scores: List[ScoredPoint] = []
        for point_id, data in collection_points_data.items():
            if data.get("vector") is None and padded_query_vector_np is not None:
                continue

            if query_filter:
                # Basic filter logic for must conditions
                if hasattr(query_filter, "must") and query_filter.must:
                    matches_filter = True
                    for condition in query_filter.must:
                        if hasattr(condition, "key") and hasattr(condition, "match"):
                            # FieldCondition with MatchValue
                            field_key = condition.key
                            match_value = (
                                condition.match.value if hasattr(condition.match, "value") else condition.match
                            )
                            payload_value = data.get("payload", {}).get(field_key)

                            # Case-insensitive matching for tag fields
                            if (
                                field_key.lower() in ["tag", "tags"]
                                and isinstance(payload_value, str)
                                and isinstance(match_value, str)
                            ):
                                matches_filter = payload_value.lower() == match_value.lower()
                            else:
                                matches_filter = payload_value == match_value

                            if not matches_filter:
                                matches_filter = False
                                break
                        elif hasattr(condition, "has_id"):
                            # HasIdCondition
                            if point_id not in condition.has_id:
                                matches_filter = False
                                break
                    if not matches_filter:
                        continue

            # Inline score calculation
            point_vector_list = data.get("vector")
            if not point_vector_list:
                score = 0.0
            else:
                point_vector_np = np.array(_pad_vector(point_vector_list))
                distance_type = collection_config.get("params", {}).get("vectors", {}).get("distance", Distance.COSINE)

                if distance_type == Distance.COSINE:
                    if np.linalg.norm(point_vector_np) > 1e-9 and np.linalg.norm(padded_query_vector_np) > 1e-9:
                        similarity = np.dot(point_vector_np, padded_query_vector_np) / (
                            np.linalg.norm(point_vector_np) * np.linalg.norm(padded_query_vector_np)
                        )
                        score = float(similarity)
                    else:
                        score = 0.0
                elif distance_type == Distance.EUCLID:
                    dist = np.linalg.norm(point_vector_np - padded_query_vector_np)
                    score = 1.0 / (1.0 + float(dist))
                elif distance_type == Distance.DOT:
                    score = float(np.dot(point_vector_np, padded_query_vector_np))
                else:
                    score = 0.0

            if score_threshold is not None and score < score_threshold:
                continue

            results_with_scores.append(
                ScoredPoint(
                    id=point_id,
                    version=0,  # Mock version
                    score=score,
                    payload=data.get("payload") if with_payload else None,
                    vector=data.get("vector") if with_vectors else None,
                )
            )

        results_with_scores.sort(key=lambda p: p.score, reverse=True)  # Higher score is better
        final_results = results_with_scores[:limit]
        # print(f"FakeQdrantClient.search: Found {len(final_results)} results. IDs: {[r.id for r in final_results]}")
        return final_results

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Union[Filter, "points_pb2.Filter", None] = None,
        limit: int = 10,
        order_by: Union[str, OrderBy, "points_pb2.OrderBy", None] = None,
        offset: Union[int, str, "points_pb2.PointId", None] = None,
        with_payload: Union[
            bool, Sequence[str], PayloadSelectorInclude, PayloadSelectorExclude, "points_pb2.WithPayloadSelector"
        ] = True,
        with_vectors: Union[bool, Sequence[str]] = False,
        consistency: Union[int, ReadConsistencyType, None] = None,
        shard_key_selector: Union[int, str, List[Union[int, str]], None] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> Tuple[List[Record], Union[int, str, "points_pb2.PointId", None]]:
        """Scrolls through points in a collection, with basic filtering and offset handling."""
        # print(f"FakeQdrantClient.scroll called for '{collection_name}'. Filter: {scroll_filter}, Limit: {limit}, Offset: {offset}")
        if collection_name not in self._collections:
            # print(f"FakeQdrantClient.scroll: Collection '{collection_name}' not found.")
            return [], None

        collection_data = self._collections[collection_name]
        all_points_in_collection = list(collection_data["points"].items())  # List of (id, data) tuples

        # Apply filter if provided
        if scroll_filter:
            filtered_points_with_ids = []
            for pid, pdata in all_points_in_collection:
                matches_filter = True
                if hasattr(scroll_filter, "must") and scroll_filter.must:
                    for condition in scroll_filter.must:
                        if hasattr(condition, "key") and hasattr(condition, "match"):
                            # FieldCondition with MatchValue
                            field_key = condition.key
                            match_value = (
                                condition.match.value if hasattr(condition.match, "value") else condition.match
                            )
                            payload_value = pdata.get("payload", {}).get(field_key)
                            if payload_value != match_value:
                                matches_filter = False
                                break
                        elif hasattr(condition, "has_id"):
                            # HasIdCondition
                            if pid not in condition.has_id:
                                matches_filter = False
                                break
                if matches_filter:
                    filtered_points_with_ids.append((pid, pdata))
        else:
            filtered_points_with_ids = all_points_in_collection

        # Determine starting point based on offset
        start_index = 0
        if offset is not None:
            found_offset_id = False
            for i, (pid, _) in enumerate(filtered_points_with_ids):
                if pid == offset:
                    start_index = i + 1  # Start after the offset ID
                    found_offset_id = True
                    break
            if not found_offset_id:
                # Offset ID not found among filtered points (e.g., it was deleted or filter changed results)
                # Depending on strictness, could return empty or log. For robust scroll, if offset not found, it implies end.
                # However, qdrant_store.py expects to continue until no points are returned from scroll.
                # If offset ID is not in the current filtered list, it might mean we scrolled past it or it never existed.
                # Returning empty effectively stops the scroll.
                # print(f"FakeQdrantClient.scroll: Offset ID '{offset}' not found in filtered points. Stopping scroll.")
                return [], None

        # Get the page of points
        end_index = start_index + limit
        page_of_points_with_ids = filtered_points_with_ids[start_index:end_index]

        result_records = []
        for point_id, point_data in page_of_points_with_ids:
            payload = point_data.get("payload") if with_payload else None
            vector = point_data.get("vector") if with_vectors else None
            # Ensure ID type matches typical Qdrant responses (e.g. string for UUIDs)
            # The mock stores IDs as they are inserted (can be int, str, uuid)
            # Record expects id: PointId which is Union[str, int, uuid.UUID]
            result_records.append(Record(id=point_id, payload=payload, vector=vector))

        next_page_offset_val: Optional[Union[int, str, uuid.UUID]] = None
        if end_index < len(filtered_points_with_ids):
            next_page_offset_val = filtered_points_with_ids[end_index][0]  # ID of the next point to start from

        # print(f"FakeQdrantClient.scroll: Returning {len(result_records)} records. Next offset: {next_page_offset_val}")
        return result_records, next_page_offset_val

    def delete(
        self,
        collection_name: str,
        points_selector: Union[
            "list[Union[int, str, points_pb2.PointId]]",
            Filter,
            "points_pb2.Filter",
            PointIdsList,
            FilterSelector,
            "points_pb2.PointsSelector",
        ],
        wait: bool = True,
        ordering: Optional[WriteOrdering] = None,
        shard_key_selector: Union[
            "Annotated[int, Strict(strict=True)]",
            "Annotated[str, Strict(strict=True)]",
            "List[Union[Annotated[int, Strict(strict=True)], Annotated[str, Strict(strict=True)]]]",
            None,
        ] = None,
        **kwargs: Any,
    ) -> UpdateResult:
        """Deletes points from a collection."""
        # print(f"FakeQdrantClient.delete: Attempting to delete from '{collection_name}'")
        if not self.collection_exists(collection_name):
            # print(f"FakeQdrantClient.delete: Collection '{collection_name}' not found.")
            return UpdateResult(operation_id=0, status="not_found")

        ids_to_delete = set()
        collection_points = self._collections[collection_name]["points"]

        if isinstance(points_selector, list):  # Direct list of IDs
            ids_to_delete.update(points_selector)
        elif isinstance(points_selector, PointsSelector):
            if points_selector.points:  # List of IDs in PointsSelector
                ids_to_delete.update(points_selector.points)
            if points_selector.filter:  # Filter in PointsSelector
                for point_id, data in list(collection_points.items()):
                    matches_filter = True
                    if hasattr(points_selector.filter, "must") and points_selector.filter.must:
                        for condition in points_selector.filter.must:
                            if hasattr(condition, "key") and hasattr(condition, "match"):
                                # FieldCondition with MatchValue
                                field_key = condition.key
                                match_value = (
                                    condition.match.value if hasattr(condition.match, "value") else condition.match
                                )
                                payload_value = data.get("payload", {}).get(field_key)
                                if payload_value != match_value:
                                    matches_filter = False
                                    break
                            elif hasattr(condition, "has_id"):
                                # HasIdCondition
                                if point_id not in condition.has_id:
                                    matches_filter = False
                                    break
                    if matches_filter:
                        ids_to_delete.add(point_id)
        elif isinstance(points_selector, Filter):  # Direct Filter object
            for point_id, data in list(collection_points.items()):
                matches_filter = True
                if hasattr(points_selector, "must") and points_selector.must:
                    for condition in points_selector.must:
                        if hasattr(condition, "key") and hasattr(condition, "match"):
                            # FieldCondition with MatchValue
                            field_key = condition.key
                            match_value = (
                                condition.match.value if hasattr(condition.match, "value") else condition.match
                            )
                            payload_value = data.get("payload", {}).get(field_key)
                            if payload_value != match_value:
                                matches_filter = False
                                break
                        elif hasattr(condition, "has_id"):
                            # HasIdCondition
                            if point_id not in condition.has_id:
                                matches_filter = False
                                break
                if matches_filter:
                    ids_to_delete.add(point_id)
        elif isinstance(points_selector, dict):  # Raw filter dictionary (for purge_all_vectors)
            # Handle raw filter dict like {"filter": {"must": []}}
            filter_dict = points_selector.get("filter", {})
            must_conditions = filter_dict.get("must", [])

            # If must is empty, it means select all points
            if not must_conditions:
                ids_to_delete.update(collection_points.keys())
            else:
                # Process must conditions (similar to Filter object handling)
                for point_id, data in list(collection_points.items()):
                    matches_filter = True
                    for condition in must_conditions:
                        if isinstance(condition, dict):
                            # Handle dict-based conditions
                            if "key" in condition and "match" in condition:
                                field_key = condition["key"]
                                match_value = condition["match"]
                                payload_value = data.get("payload", {}).get(field_key)
                                if payload_value != match_value:
                                    matches_filter = False
                                    break
                        elif hasattr(condition, "key") and hasattr(condition, "match"):
                            # Handle object-based conditions
                            field_key = condition.key
                            match_value = (
                                condition.match.value if hasattr(condition.match, "value") else condition.match
                            )
                            payload_value = data.get("payload", {}).get(field_key)
                            if payload_value != match_value:
                                matches_filter = False
                                break
                    if matches_filter:
                        ids_to_delete.add(point_id)
        else:
            # print(f"FakeQdrantClient.delete: Unrecognized points_selector type: {type(points_selector)}")
            return UpdateResult(operation_id=0, status="completed")

        deleted_count = 0
        actually_deleted_ids_log = []
        if ids_to_delete:
            for point_id_to_delete in ids_to_delete:
                # Handle potential type mismatches (str '123' vs int 123)
                resolved_id = None
                if point_id_to_delete in collection_points:
                    resolved_id = point_id_to_delete
                elif (
                    isinstance(point_id_to_delete, str)
                    and point_id_to_delete.isdigit()
                    and int(point_id_to_delete) in collection_points
                ):
                    resolved_id = int(point_id_to_delete)
                elif isinstance(point_id_to_delete, int) and str(point_id_to_delete) in collection_points:
                    resolved_id = str(point_id_to_delete)

                if resolved_id is not None and resolved_id in collection_points:
                    del collection_points[resolved_id]
                    deleted_count += 1
                    actually_deleted_ids_log.append(resolved_id)

        # print(f"FakeQdrantClient.delete: Deleted {deleted_count} points from '{collection_name}'. IDs: {actually_deleted_ids_log}.")
        return UpdateResult(operation_id=random.randint(1, 1000), status="completed")

    def delete_points(
        self,
        collection_name: str,
        points_selector: Union[PointsSelector, dict],
        wait: bool = True,
        **kwargs: Any,
    ) -> UpdateResult:
        """Deletes points from a collection. This is an alias for the delete method."""
        return self.delete(collection_name, points_selector, wait, **kwargs)

    def count(
        self,
        collection_name: str,
        count_filter: Union[Filter, "points_pb2.Filter", None] = None,
        exact: bool = True,
        shard_key_selector: Union[
            "Annotated[int, Strict(strict=True)]",
            "Annotated[str, Strict(strict=True)]",
            "List[Union[Annotated[int, Strict(strict=True)], Annotated[str, Strict(strict=True)]]]",
            None,
        ] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> CountResult:
        """Counts points in a collection, optionally with a filter."""
        # print(f"FakeQdrantClient.count: Counting in '{collection_name}', filter: {count_filter is not None}")
        if not self.collection_exists(collection_name):
            # print(f"FakeQdrantClient.count: Collection '{collection_name}' not found.")
            return CountResult(count=0)

        collection_points = self._collections[collection_name]["points"]
        if not count_filter:
            return CountResult(count=len(collection_points))

        # Count with filtering
        count = 0
        for point_id, data in collection_points.items():
            matches_filter = True
            if count_filter and hasattr(count_filter, "must") and count_filter.must:
                for condition in count_filter.must:
                    if hasattr(condition, "key") and hasattr(condition, "match"):
                        # FieldCondition with MatchValue
                        field_key = condition.key
                        match_value = condition.match.value if hasattr(condition.match, "value") else condition.match
                        payload_value = data.get("payload", {}).get(field_key)
                        if payload_value != match_value:
                            matches_filter = False
                            break
                    elif hasattr(condition, "has_id"):
                        # HasIdCondition
                        if point_id not in condition.has_id:
                            matches_filter = False
                            break
            if matches_filter:
                count += 1

        # print(f"FakeQdrantClient.count: Count = {count} for collection '{collection_name}'.")
        return CountResult(count=count)

    def create_payload_index(
        self,
        collection_name: str,
        field_name: str,
        field_schema: Union[
            PayloadSchemaType,
            KeywordIndexParams,
            IntegerIndexParams,
            FloatIndexParams,
            GeoIndexParams,
            TextIndexParams,
            BoolIndexParams,
            DatetimeIndexParams,
            UuidIndexParams,
            int,
            "collections_pb2.PayloadIndexParams",
            None,
        ] = None,
        field_type: Union[
            PayloadSchemaType,
            KeywordIndexParams,
            IntegerIndexParams,
            FloatIndexParams,
            GeoIndexParams,
            TextIndexParams,
            BoolIndexParams,
            DatetimeIndexParams,
            UuidIndexParams,
            int,
            "collections_pb2.PayloadIndexParams",
            None,
        ] = None,
        wait: bool = True,
        ordering: Optional[WriteOrdering] = None,
        **kwargs: Any,
    ) -> UpdateResult:
        """Mocks creating a payload index. For this mock, it just notes the field."""
        if not self.collection_exists(collection_name):
            # print(f"FakeQdrantClient.create_payload_index: Collection '{collection_name}' not found.")
            return UpdateResult(operation_id=0, status="not_found")

        self._collections[collection_name].setdefault("indexed_fields", set()).add(field_name)
        # print(f"FakeQdrantClient.create_payload_index: 'Indexed' field '{field_name}' in '{collection_name}'. Schema: {field_schema}")
        return UpdateResult(operation_id=random.randint(1, 1000), status="completed")

    # Other QdrantClient methods that might be needed by QdrantStore or tests:
    # - get_aliases
    # - update_collection_aliases
    # - delete_alias
    # - list_snapshots
    # - create_snapshot
    # - delete_snapshot
    # - list_full_snapshots
    # - create_full_snapshot
    # - delete_full_snapshot
    # - recover_snapshot
    # - update_collection # For changing collection params
    # - recommend # Recommendation API
    # - search_batch # Batch search
    # - recommend_batch # Batch recommend
    # - delete_payload_keys
    # - set_payload
    # - clear_payload
    # - get_points_count (use self.count with no filter)
    # - etc.
    # For now, only implementing methods explicitly mentioned or implied by the prompt.

    # Add missing methods to match real QdrantClient
    def add(self, *args, **kwargs):
        """Placeholder for add method"""
        return UpdateResult(operation_id=1, status="completed")

    def batch_update_points(self, *args, **kwargs):
        """Placeholder for batch_update_points method"""
        return UpdateResult(operation_id=1, status="completed")

    def clear_payload(self, *args, **kwargs):
        """Placeholder for clear_payload method"""
        return UpdateResult(operation_id=1, status="completed")

    def create_full_snapshot(self, *args, **kwargs):
        """Placeholder for create_full_snapshot method"""
        return {"snapshot_id": "fake_snapshot"}

    def create_shard_key(self, *args, **kwargs):
        """Placeholder for create_shard_key method"""
        return UpdateResult(operation_id=1, status="completed")

    def create_shard_snapshot(self, *args, **kwargs):
        """Placeholder for create_shard_snapshot method"""
        return {"snapshot_id": "fake_shard_snapshot"}

    def create_snapshot(self, *args, **kwargs):
        """Placeholder for create_snapshot method"""
        return {"snapshot_id": "fake_snapshot"}

    def delete_full_snapshot(self, *args, **kwargs):
        """Placeholder for delete_full_snapshot method"""
        return True

    def delete_payload(self, *args, **kwargs):
        """Placeholder for delete_payload method"""
        return UpdateResult(operation_id=1, status="completed")

    def delete_payload_index(self, *args, **kwargs):
        """Placeholder for delete_payload_index method"""
        return UpdateResult(operation_id=1, status="completed")

    def delete_shard_key(self, *args, **kwargs):
        """Placeholder for delete_shard_key method"""
        return UpdateResult(operation_id=1, status="completed")

    def delete_shard_snapshot(self, *args, **kwargs):
        """Placeholder for delete_shard_snapshot method"""
        return True

    def delete_snapshot(self, *args, **kwargs):
        """Placeholder for delete_snapshot method"""
        return True

    def delete_vectors(self, *args, **kwargs):
        """Placeholder for delete_vectors method"""
        return UpdateResult(operation_id=1, status="completed")

    def discover(self, *args, **kwargs):
        """Placeholder for discover method"""
        return []

    def discover_batch(self, *args, **kwargs):
        """Placeholder for discover_batch method"""
        return []

    def facet(self, *args, **kwargs):
        """Placeholder for facet method"""
        return {}

    def get_aliases(self, *args, **kwargs):
        """Placeholder for get_aliases method"""
        return {}

    def get_collection_aliases(self, *args, **kwargs):
        """Placeholder for get_collection_aliases method"""
        return {}

    def get_collections(self, *args, **kwargs):
        """Placeholder for get_collections method"""
        return self.list_collections(**kwargs)

    def get_embedding_size(self, *args, **kwargs):
        """Placeholder for get_embedding_size method"""
        return VECTOR_DIMENSION

    def get_fastembed_sparse_vector_params(self, *args, **kwargs):
        """Placeholder for get_fastembed_sparse_vector_params method"""
        return {}

    def get_fastembed_vector_params(self, *args, **kwargs):
        """Placeholder for get_fastembed_vector_params method"""
        return {}

    def get_locks(self, *args, **kwargs):
        """Placeholder for get_locks method"""
        return []

    def get_sparse_vector_field_name(self, *args, **kwargs):
        """Placeholder for get_sparse_vector_field_name method"""
        return "sparse_vector"

    def get_vector_field_name(self, *args, **kwargs):
        """Placeholder for get_vector_field_name method"""
        return "vector"

    def info(self, *args, **kwargs):
        """Placeholder for info method"""
        return {"version": "fake_version"}

    def list_full_snapshots(self, *args, **kwargs):
        """Placeholder for list_full_snapshots method"""
        return []

    def list_shard_snapshots(self, *args, **kwargs):
        """Placeholder for list_shard_snapshots method"""
        return []

    def list_snapshots(self, *args, **kwargs):
        """Placeholder for list_snapshots method"""
        return []

    def lock_storage(self, *args, **kwargs):
        """Placeholder for lock_storage method"""
        return True

    def migrate(self, *args, **kwargs):
        """Placeholder for migrate method"""
        return UpdateResult(operation_id=1, status="completed")

    def overwrite_payload(self, *args, **kwargs):
        """Placeholder for overwrite_payload method"""
        return UpdateResult(operation_id=1, status="completed")

    def query(self, *args, **kwargs):
        """Placeholder for query method"""
        return []

    def query_batch(self, *args, **kwargs):
        """Placeholder for query_batch method"""
        return []

    def query_batch_points(self, *args, **kwargs):
        """Placeholder for query_batch_points method"""
        return []

    def query_points(self, *args, **kwargs):
        """Placeholder for query_points method"""
        return []

    def query_points_groups(self, *args, **kwargs):
        """Placeholder for query_points_groups method"""
        return []

    def recommend(self, *args, **kwargs):
        """Placeholder for recommend method"""
        return []

    def recommend_batch(self, *args, **kwargs):
        """Placeholder for recommend_batch method"""
        return []

    def recommend_groups(self, *args, **kwargs):
        """Placeholder for recommend_groups method"""
        return []

    def recover_shard_snapshot(self, *args, **kwargs):
        """Placeholder for recover_shard_snapshot method"""
        return True

    def recover_snapshot(self, *args, **kwargs):
        """Placeholder for recover_snapshot method"""
        return True

    def recreate_collection(self, *args, **kwargs):
        """Placeholder for recreate_collection method"""
        return True

    def search_batch(self, *args, **kwargs):
        """Placeholder for search_batch method"""
        return []

    def search_groups(self, *args, **kwargs):
        """Placeholder for search_groups method"""
        return []

    def search_matrix_offsets(self, *args, **kwargs):
        """Placeholder for search_matrix_offsets method"""
        return []

    def search_matrix_pairs(self, *args, **kwargs):
        """Placeholder for search_matrix_pairs method"""
        return []

    def set_model(self, *args, **kwargs):
        """Placeholder for set_model method"""
        return True

    def set_payload(self, *args, **kwargs):
        """Placeholder for set_payload method"""
        return UpdateResult(operation_id=1, status="completed")

    def set_sparse_model(self, *args, **kwargs):
        """Placeholder for set_sparse_model method"""
        return True

    def unlock_storage(self, *args, **kwargs):
        """Placeholder for unlock_storage method"""
        return True

    def update_collection(self, *args, **kwargs):
        """Placeholder for update_collection method"""
        return True

    def update_collection_aliases(self, *args, **kwargs):
        """Placeholder for update_collection_aliases method"""
        return True

    def update_vectors(self, *args, **kwargs):
        """Placeholder for update_vectors method"""
        return UpdateResult(operation_id=1, status="completed")

    def upload_collection(self, *args, **kwargs):
        """Placeholder for upload_collection method"""
        return True

    def upload_points(self, *args, **kwargs):
        """Placeholder for upload_points method"""
        return UpdateResult(operation_id=1, status="completed")

    def upload_records(self, *args, **kwargs):
        """Placeholder for upload_records method"""
        return UpdateResult(operation_id=1, status="completed")

    # Add private methods that are in the real client
    def _embed_documents(self, *args, **kwargs):
        """Placeholder for _embed_documents method"""
        return []

    def _embed_models(self, *args, **kwargs):
        """Placeholder for _embed_models method"""
        return []

    def _embed_models_strict(self, *args, **kwargs):
        """Placeholder for _embed_models_strict method"""
        return []

    def _get_or_init_image_model(self, *args, **kwargs):
        """Placeholder for _get_or_init_image_model method"""
        return None

    def _get_or_init_late_interaction_model(self, *args, **kwargs):
        """Placeholder for _get_or_init_late_interaction_model method"""
        return None

    def _get_or_init_model(self, *args, **kwargs):
        """Placeholder for _get_or_init_model method"""
        return None

    def _get_or_init_sparse_model(self, *args, **kwargs):
        """Placeholder for _get_or_init_sparse_model method"""
        return None

    def _points_iterator(self, *args, **kwargs):
        """Placeholder for _points_iterator method"""
        return iter([])

    def _resolve_query_batch_request(self, *args, **kwargs):
        """Placeholder for _resolve_query_batch_request method"""
        return {}

    def _resolve_query_request(self, *args, **kwargs):
        """Placeholder for _resolve_query_request method"""
        return {}

    def _scored_points_to_query_responses(self, *args, **kwargs):
        """Placeholder for _scored_points_to_query_responses method"""
        return []

    def _sparse_embed_documents(self, *args, **kwargs):
        """Placeholder for _sparse_embed_documents method"""
        return []

    def _validate_collection_info(self, *args, **kwargs):
        """Placeholder for _validate_collection_info method"""
        return True
