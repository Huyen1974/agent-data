from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, Field, field_validator, constr, model_validator
from typing import List, Optional, Any, Dict, Literal, Union
import os
from agent_data.vector_store.qdrant_store import QdrantStore
import logging
import asyncio
import openai  # Added for OpenAI
import time
from prometheus_client import Counter, Histogram, make_asgi_app

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("api_requests_total", "Total API requests", ["endpoint", "method", "status_code"])
REQUEST_LATENCY = Histogram("api_request_duration_seconds", "Request latency in seconds", ["endpoint", "method"])

# Environment variables for Qdrant connection (consider a config file/class for larger apps)
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "my_collection")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # Added for OpenAI
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002")  # Added


# Helper function to generate OpenAI embeddings
async def _generate_openai_embedding(text: str, model: str = OPENAI_EMBEDDING_MODEL) -> Dict[str, Any]:
    """Internal helper to generate embeddings using OpenAI API."""
    try:
        response = await asyncio.to_thread(openai.embeddings.create, input=text, model=model)
        # Assuming response.data[0].embedding exists and is the correct structure
        return {"embedding": response.data[0].embedding, "model": model, "text": text}
    except openai.APIError as oe:
        logger.error(f"OpenAI API error in _generate_openai_embedding for text '{text[:50]}...': {oe}")
        # Re-raise to be caught by the calling handler, or handle more specifically if needed
        raise
    except Exception as e:
        logger.error(f"Unexpected error in _generate_openai_embedding for text '{text[:50]}...': {e}")
        # Re-raise to be caught by the calling handler
        raise


app = FastAPI(title="Vector Search API", description="API for vector search using QdrantStore and OpenAI Embeddings")

# Mount Prometheus metrics endpoint
app.mount("/metrics", make_asgi_app())

# Metrics middleware


@app.middleware("http")
async def add_metrics_middleware(request: Request, call_next):
    """Middleware to collect Prometheus metrics for API requests."""
    start_time = time.time()
    endpoint = request.url.path
    method = request.method

    # Process the request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Record metrics
    REQUEST_COUNT.labels(endpoint=endpoint, method=method, status_code=response.status_code).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

    return response


# Initialize OpenAI client
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.warning("OPENAI_API_KEY environment variable not set. Embedding generation will fail.")
    # Optionally, could raise an error here or disable embedding endpoints if key is critical


class VectorSearchRequest(BaseModel):
    query_vector: List[float] = Field(..., description="Vector to search for (embedding)")
    top_k: Optional[int] = Field(5, description="Number of results to return")
    filter_tag: Optional[str] = Field(None, description="Optional tag to filter results")
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("query_vector")
    @classmethod
    def validate_vector_dimension(cls, v):
        if len(v) != 1536:
            raise ValueError(f"Vector must have 1536 dimensions, got {len(v)}")
        return v

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v):
        if v is not None and v <= 0:
            raise ValueError(f"top_k must be positive, got {v}")
        return v


class VectorUpsertRequest(BaseModel):
    point_id: int = Field(..., description="Unique identifier for the vector point")
    vector: List[float] = Field(..., description="Vector to upsert (embedding)")
    metadata: Dict[str, Any] = Field(..., description="Metadata associated with the vector")

    @field_validator("vector")
    @classmethod
    def validate_vector_dimension(cls, v):
        if len(v) != 1536:
            raise ValueError(f"Vector must have 1536 dimensions, got {len(v)}")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v):
        if "tag" not in v:
            raise ValueError("Metadata must contain a 'tag' field")
        return v


class DeleteVectorRequest(BaseModel):
    point_id: int = Field(..., description="Unique identifier for the vector point to delete")


class HealthResponse(BaseModel):
    status: str


# Pydantic models for /query_vectors_by_tag
class QueryByTagRequest(BaseModel):
    tag: str = Field(..., description="Tag to filter vectors by")
    offset: Optional[int] = Field(0, ge=0, description="Offset for pagination")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Limit for pagination (max 100)")


class QueryByTagResponseItem(BaseModel):
    id: Any  # Qdrant IDs can be int or UUID
    payload: Dict[str, Any]
    # vector field is omitted as per requirements (vector: null)


class QueryByTagResponse(BaseModel):
    status: str
    results: List[QueryByTagResponseItem]
    count: int
    offset: int
    limit: int


# Pydantic models for /count_vectors_by_tag
class CountByTagRequest(BaseModel):
    tag: str = Field(..., min_length=1, description="Tag to count vectors by. Cannot be empty.")


class CountByTagResponse(BaseModel):
    status: str
    count: int
    tag: str


# Pydantic model for /list_all_tags
class ListAllTagsResponse(BaseModel):
    status: str  # Literal["ok"] - Using str for now, can refine to Literal if needed
    tags: List[str]


# Pydantic models for /delete_vectors_by_tag
class DeleteByTagRequest(BaseModel):
    tag: constr(min_length=1) = Field(..., description="Tag to delete vectors by. Cannot be empty.")


class DeleteByTagResponse(BaseModel):
    status: Literal["ok"]
    deleted: int
    tag: str


class PurgeAllResponse(BaseModel):
    status: Literal["ok"]
    deleted: int


# Pydantic models for /get_vector_by_id
class GetVectorByIdRequest(BaseModel):
    point_id: Union[int, str] = Field(
        ..., description="Unique identifier for the vector point to retrieve (can be int or string UUID)."
    )


class VectorPoint(BaseModel):
    id: Any  # Qdrant IDs can be int or UUID
    vector: List[float]
    metadata: Dict[str, Any]


class GetVectorByIdResponse(BaseModel):
    status: Literal["ok"]
    point: VectorPoint


# Pydantic models for /get_vector_ids_by_tag
class GetVectorIdsByTagRequest(BaseModel):
    tag: constr(min_length=1) = Field(..., description="Tag to filter vector IDs by. Cannot be empty.")


class GetVectorIdsByTagResponse(BaseModel):
    status: Literal["ok"]
    point_ids: List[Any]  # Qdrant IDs can be int or UUID


# Pydantic models for /query_vectors_by_ids
class QueryVectorsByIdsRequest(BaseModel):
    point_ids: List[Union[int, str]] = Field(..., description="List of point IDs to query for.")
    # limit is not strictly needed here as we fetch specific IDs, but kept for consistency if desired for API shape
    # limit: Optional[int] = Field(10, description="Maximum number of points to return from the provided IDs list")


class QueryVectorsByIdsResponseItem(BaseModel):
    id: Any
    vector: List[float]
    payload: Dict[str, Any]


# Pydantic models for /update_vector
class UpdateVectorRequest(BaseModel):
    point_id: Union[int, str] = Field(
        ..., description="Unique identifier for the vector point to update (can be int or string)."
    )
    new_vector: List[float] = Field(..., description="New vector embedding, must have 1536 dimensions.")
    new_metadata: Dict[str, Any] = Field(..., description="New metadata to associate with the vector. Cannot be empty.")

    @field_validator("new_vector")
    @classmethod
    def validate_new_vector_dimension(cls, v):
        if len(v) != 1536:
            raise ValueError(f"New vector must have 1536 dimensions, got {len(v)}")
        return v

    @field_validator("new_metadata")
    @classmethod
    def validate_new_metadata_not_empty(cls, v):
        if not v:
            raise ValueError("New metadata cannot be empty")
        return v


class UpdateVectorResponse(BaseModel):
    status: Literal["ok"]
    updated: bool


# Pydantic models for /generate_embedding_real
class GenerateEmbeddingRequest(BaseModel):
    text: str = Field(..., description="Text to generate an embedding for.")
    # Optionally, could add a model override here if needed


class GenerateEmbeddingResponse(BaseModel):
    text: str
    embedding: List[float]
    model: str


class SemanticSearchRequest(BaseModel):
    query_text: str = Field(
        ...,
        max_length=2048,
        description="The text to search for.",
        json_schema_extra={"example": "What are the latest advancements in AI?"},
    )
    top_k: Optional[int] = Field(
        default=10,
        gt=0,
        le=100,
        description="The maximum number of search results to return.",
        json_schema_extra={"example": 5},
    )
    filter_tag: Optional[str] = Field(
        None,
        max_length=64,
        description="Optional metadata tag to filter the search results. Only vectors with this tag will be considered. Max 64 chars.",
        json_schema_extra={"example": "technology"},
    )
    score_threshold: Optional[float] = Field(None, description="Optional score threshold to filter results")
    collection_name: Optional[str] = Field(None, description="Optional Qdrant collection name to search in.")

    @field_validator("query_text")
    @classmethod
    def validate_query_text_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query_text cannot be empty or just whitespace")
        return value

    @field_validator("filter_tag")
    @classmethod
    def validate_filter_tag_length(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        stripped_value = value.strip()  # Strip whitespace

        if not stripped_value:  # Check if empty after stripping
            raise ValueError("filter_tag, if provided, cannot be empty or just whitespace")

        # Removed explicit length check here, Pydantic's `max_length=64` on Field will handle it.
        # if len(stripped_value) > 64:
        #     raise ValueError("filter_tag cannot exceed 64 characters")

        return stripped_value  # Return stripped value

    @field_validator("score_threshold")
    @classmethod
    def validate_score_threshold(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0 <= v <= 1):
            raise ValueError("score_threshold must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def _require_tag_or_threshold_or_collection(cls, model_instance: "SemanticSearchRequest"):
        if (
            model_instance.score_threshold is None
            and model_instance.filter_tag is None
            and model_instance.collection_name is None
        ):
            raise ValueError(
                "At least one of 'filter_tag', 'score_threshold', or 'collection_name' must be provided for semantic search."
            )

        if model_instance.collection_name is not None and (
            model_instance.score_threshold is not None or model_instance.filter_tag is not None
        ):
            pass
        return model_instance


class SemanticSearchResultItem(BaseModel):
    id: Union[str, int]  # Qdrant IDs can be int or UUID
    score: float
    payload: Dict[str, Any]  # Expected to contain 'original_text', 'tag' etc.


class SemanticSearchResponse(BaseModel):
    status: Literal["ok"]
    count: int
    results: List[SemanticSearchResultItem]


class ClearEmbeddingsRequest(BaseModel):
    # How to specify what to clear? By tag? All?
    # For now, let's assume by tag, or all if tag is not provided.
    # A more specific endpoint like /clear_embeddings_by_tag might be better.
    # Or a single /clear_embeddings that can clear all if no specific filter.
    # The prompt mentions "/clear_embeddings", suggesting a general clear.
    # Let's make it clear ALL for now, similar to purge_all_vectors
    pass  # No specific parameters for now, implies clearing all.


class ClearEmbeddingsResponse(BaseModel):
    status: Literal["ok"]
    deleted_count: int


def get_qdrant_store():
    """Dependency to get QdrantStore instance"""
    try:
        store = QdrantStore()
        return store
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize QdrantStore: {str(e)}")


@app.post("/search_vector", response_model=Dict[str, Any])
async def search_vector(request: VectorSearchRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Search for vectors in the Qdrant collection that are similar to the query vector.

    Args:
        request: Vector search request containing query_vector, top_k, and filter_tag

    Returns:
        List of search results with point IDs and payloads
    """
    try:
        # Perform search
        results = qdrant_store.search_vector(
            query_vector=request.query_vector, top_k=request.top_k, filter_tag=request.filter_tag
        )

        # Format results for API response
        formatted_results = [{"id": point.id, "score": point.score, "payload": point.payload} for point in results]

        return {"status": "success", "count": len(formatted_results), "results": formatted_results}

    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Error searching vectors: {str(e)}")


@app.post("/upsert_vector", response_model=Dict[str, Any])
async def upsert_vector(request: VectorUpsertRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Upsert (insert or update) a vector into the Qdrant collection.

    Args:
        request: Vector upsert request containing point_id, vector, and metadata

    Returns:
        Success status with the point ID
    """
    try:
        # Perform upsert
        result = await qdrant_store.upsert_vector(
            point_id=request.point_id, vector=request.vector, metadata=request.metadata
        )

        if result:
            return {"status": "ok", "point_id": request.point_id}
        else:
            raise HTTPException(status_code=500, detail="Upsert operation did not return success")

    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(status_code=500, detail=f"Error upserting vector: {str(e)}")


@app.post("/delete_vector", response_model=Dict[str, Any])
async def delete_vector(request: DeleteVectorRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Delete a vector from the Qdrant collection by its point ID.

    Args:
        request: Vector delete request containing point_id

    Returns:
        Success status with the deleted point ID
    """
    try:
        # Perform delete
        result = await qdrant_store.delete_vector(point_id=request.point_id)

        if result:
            return {"status": "deleted", "point_id": request.point_id}
        else:
            # This case might not be reachable if Qdrant client raises an error on failure
            raise HTTPException(
                status_code=500,  # Or 404 if point_id not found and qdrant_store handles it
                detail="Delete operation did not return success or point not found",
            )

    except Exception as e:
        # Handle unexpected errors
        # Log the error for debugging
        logger.error(f"Error deleting vector: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error deleting vector: {str(e)}"  # Consider more specific error codes if possible
        )


@app.post("/query_vectors_by_tag", response_model=QueryByTagResponse)
async def query_vectors_by_tag(request: QueryByTagRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Retrieve vectors by a specific tag, with pagination.
    Filters vectors based on the 'tag' field in their metadata.
    .cursor: CLI27_query_by_tag_api_added
    """
    try:
        if not request.tag:  # Technically Pydantic should catch empty string if min_length=1 is set on field
            raise HTTPException(status_code=400, detail="Tag cannot be empty.")

        results = qdrant_store.query_vectors_by_tag(tag=request.tag, offset=request.offset, limit=request.limit)

        # Transform Qdrant PointStructs to the response model
        # Qdrant's scroll returns a list of PointStruct
        response_items = [
            QueryByTagResponseItem(id=point.id, payload=point.payload if point.payload else {}) for point in results
        ]

        return QueryByTagResponse(
            status="ok", results=response_items, count=len(response_items), offset=request.offset, limit=request.limit
        )
    except HTTPException as http_exc:  # Re-raise HTTPExceptions directly
        raise http_exc
    except ValueError as ve:  # Catch Pydantic validation errors if any slip through or other ValueErrors
        logger.warning(f"Validation error in query_vectors_by_tag: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error querying vectors by tag '{request.tag}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred while querying vectors by tag: {str(e)}"
        )


@app.post("/count_vectors_by_tag", response_model=CountByTagResponse)
async def count_vectors_by_tag(request: CountByTagRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Count vectors by a specific tag.
    .cursor: CLI28_count_by_tag_api_added
    """
    try:
        # The Pydantic model `CountByTagRequest` already validates that the tag is not empty (min_length=1).
        # No need for an additional `if not request.tag:` check here.

        count = qdrant_store.count_vectors_by_tag(tag=request.tag)

        return CountByTagResponse(status="ok", count=count, tag=request.tag)
    except ValueError as ve:  # Catch Pydantic validation errors or others explicitly raised
        # This might be redundant if FastAPI handles Pydantic validation errors by default with 422.
        # However, it can catch other ValueErrors if qdrant_store.count_vectors_by_tag raises one.
        logger.warning(f"Validation error in count_vectors_by_tag: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error counting vectors by tag '{request.tag}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred while counting vectors by tag: {str(e)}"
        )


@app.post("/list_all_tags", response_model=ListAllTagsResponse)
async def list_all_tags(qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    List all unique tags present in the vector collection.
    The request body is empty for this endpoint.
    .cursor: CLI29_list_all_tags_api_added
    """
    try:
        tags = qdrant_store.list_all_tags()
        return ListAllTagsResponse(status="ok", tags=tags)
    except Exception as e:
        logger.error(f"Error listing all tags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while listing all tags: {str(e)}")


@app.post("/delete_vectors_by_tag", response_model=DeleteByTagResponse)
async def delete_vectors_by_tag(request: DeleteByTagRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Delete vectors by a specific tag.
    .cursor: CLI30_delete_by_tag_api_added
    """
    try:
        # Pydantic model `DeleteByTagRequest` already validates that tag is not empty.
        deleted_count = await qdrant_store.delete_vectors_by_tag(tag=request.tag)
        return DeleteByTagResponse(status="ok", deleted=deleted_count, tag=request.tag)
    except Exception as e:
        logger.error(f"Error deleting vectors by tag '{request.tag}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred while deleting vectors by tag: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint. Returns a static JSON response indicating the service is up.
    This endpoint is independent of external services like Qdrant.
    """
    return HealthResponse(status="ok")
    # .cursor: CLI25_health_endpoint_defined_verified


async def purge_all_vectors_from_store(vector_store: QdrantStore = Depends(get_qdrant_store)) -> PurgeAllResponse:
    """
    Deletes all vectors from the Qdrant collection.
    """
    try:
        logger.info("Received request to purge all vectors.")
        deleted_count = await vector_store.purge_all_vectors()
        logger.info(f"Successfully purged {deleted_count} vectors.")
        return PurgeAllResponse(status="ok", deleted=deleted_count)
    except Exception as e:
        logger.error(f"Error purging all vectors: {e}", exc_info=True)
        # Consider raising a more specific HTTP error or using a generic one
        raise HTTPException(status_code=500, detail=f"Failed to purge all vectors: {str(e)}")


# Register the new endpoint
app.add_api_route(
    "/purge_all_vectors",
    purge_all_vectors_from_store,
    methods=["POST"],
    response_model=PurgeAllResponse,
    summary="Purge All Vectors",
    description="Deletes all vectors from the collection. This is a destructive operation.",
    tags=["Vector Operations - Admin"],  # Assuming a tag for admin operations
)


@app.post("/get_vector_by_id", response_model=GetVectorByIdResponse)
async def get_vector_by_id_from_store(
    request: GetVectorByIdRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    Retrieve a single vector and its metadata by its point ID.
    """
    try:
        logger.info(f"Received request to get vector by ID: {request.point_id}")
        # Convert to thread to avoid blocking the event loop if QdrantStore is synchronous
        point_data = await asyncio.to_thread(qdrant_store.get_vector_by_id, request.point_id)

        if point_data:
            # Ensure vector and payload are not None, provide defaults if necessary
            # The Qdrant client's retrieve method might return PointStruct where vector/payload can be None
            # if not specifically requested or if they don't exist.
            # However, our get_vector_by_id method in QdrantStore should ensure these are fetched.
            retrieved_vector = point_data.get("vector")
            retrieved_payload = point_data.get("payload")

            if retrieved_vector is None or retrieved_payload is None:
                logger.error(f"Vector or payload missing for point ID {request.point_id} after retrieval.")
                raise HTTPException(
                    status_code=404,
                    detail=f"Vector data incomplete for point ID {request.point_id}. Vector or payload is missing.",
                )

            vector_point = VectorPoint(
                id=point_data["id"], vector=retrieved_vector, metadata=retrieved_payload  # id should always be present
            )
            logger.info(f"Successfully retrieved vector ID: {request.point_id}")
            return GetVectorByIdResponse(status="ok", point=vector_point)
        else:
            logger.warning(f"Vector ID: {request.point_id} not found.")
            raise HTTPException(status_code=404, detail=f"Vector with ID {request.point_id} not found")

    except HTTPException as http_exc:  # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        logger.error(f"Error retrieving vector ID {request.point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve vector by ID: {str(e)}")


@app.post("/get_vector_ids_by_tag", response_model=GetVectorIdsByTagResponse)
async def get_vector_ids_by_tag_from_store(
    request: GetVectorIdsByTagRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    try:
        point_ids = qdrant_store.get_vector_ids_by_tag(tag=request.tag)  # This is a sync method
        return GetVectorIdsByTagResponse(status="ok", point_ids=point_ids)
    except Exception as e:
        logger.error(f"Error getting vector IDs by tag '{request.tag}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query_vectors_by_ids", response_model=List[QueryVectorsByIdsResponseItem])
async def query_vectors_by_ids_handler(
    request: QueryVectorsByIdsRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    Retrieve multiple vectors by their specific IDs.
    Only returns points that are found.
    """
    try:
        # The QdrantStore method get_vectors_by_ids is synchronous
        # If it were async, we'd await it.
        # For synchronous methods called in async FastAPI routes, FastAPI runs them in a thread pool.
        points_data = qdrant_store.get_vectors_by_ids(point_ids=request.point_ids)

        # Transform data to match QueryVectorsByIdsResponseItem if necessary
        # The current QdrantStore method returns a list of dicts already matching this structure.
        # [{ "id": ..., "vector": ..., "payload": ...}, ...]
        return [QueryVectorsByIdsResponseItem(**p) for p in points_data]
    except Exception as e:
        logger.error(f"Error querying vectors by IDs {request.point_ids}: {e}", exc_info=True)
        # According to test, if something goes wrong or no points, it might expect 404 or empty list with 200.
        # The test expects 200 and an empty list if the point is not found (when mixed valid/invalid).
        # If the store method returns empty list on error or not found, this will naturally return 200 OK with [].
        # If store raises an error that isn't caught and returns [], FastAPI will 500.
        # Current store method get_vectors_by_ids returns [] on Qdrant error.
        # So this should align with test if an error in store means "not found" for this context.
        # However, a true server error should still be a 500.
        # Let's ensure an explicit 500 for unexpected errors here.
        raise HTTPException(status_code=500, detail=f"Error processing query_vectors_by_ids: {str(e)}")


@app.post("/update_vector", response_model=UpdateVectorResponse)
async def update_vector_handler(request: UpdateVectorRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)):
    """
    Update an existing vector and its metadata in the Qdrant collection.
    This operation will also sync metadata with Firestore if enabled.
    """
    try:
        success = await qdrant_store.update_vector(
            point_id=request.point_id, new_vector=request.new_vector, new_metadata=request.new_metadata
        )
        if success:
            return UpdateVectorResponse(status="ok", updated=True)
        else:
            # This case should ideally not be reached if update_vector raises exceptions on failure
            # or if False implies a specific non-exceptional failure handled by QdrantStore.
            # For now, assume False means something went wrong that wasn't an exception.
            logger.warning(f"qdrant_store.update_vector returned False for point_id: {request.point_id}")
            raise HTTPException(
                status_code=500,  # Or a more specific error code if applicable
                detail=f"Failed to update vector for point_id: {request.point_id}. Operation did not confirm success.",
            )
    except ValueError as ve:  # Catch Pydantic validation errors or other ValueErrors
        logger.error(f"Validation error updating vector for point_id {request.point_id}: {ve}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))
    except HTTPException:  # Re-raise HTTPExceptions if they are already handled
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating vector for point_id {request.point_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while updating vector: {str(e)}")


@app.post("/generate_embedding_real", response_model=GenerateEmbeddingResponse)
async def generate_embedding_real_handler(request: GenerateEmbeddingRequest):
    """
    Generates an embedding for the given text using a real OpenAI model.
    """
    if not openai.api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured. Cannot generate embeddings.")
    try:
        response = openai.embeddings.create(input=request.text, model=OPENAI_EMBEDDING_MODEL)
        embedding = response.data[0].embedding
        return GenerateEmbeddingResponse(text=request.text, embedding=embedding, model=OPENAI_EMBEDDING_MODEL)
    except openai.APIError as e:
        logger.error(f"OpenAI API error during embedding generation: {e}", exc_info=True)
        raise HTTPException(status_code=e.status_code or 500, detail=f"OpenAI API error: {e.message or str(e)}")
    except Exception as e:
        logger.error(f"Error generating embedding for text '{request.text}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate embedding: {str(e)}")


@app.post("/semantic_search_cosine", response_model=SemanticSearchResponse)
async def semantic_search_cosine_handler(
    request: SemanticSearchRequest, qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    Performs a semantic search using cosine similarity.
    Generates an embedding for the query_text and then searches Qdrant.
    """
    logger.info(
        f"Received semantic search request for text: '{request.query_text[:50]}...', top_k: {request.top_k}, filter_tag: {request.filter_tag}, score_threshold: {request.score_threshold}, collection_name: {request.collection_name}"
    )

    if request.top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    try:
        # Generate embedding for the query text
        embedding_response = await _generate_openai_embedding(request.query_text)
        query_vector = embedding_response["embedding"]

        # Perform search in Qdrant
        search_results = qdrant_store.search_vector(
            query_vector=query_vector,
            top_k=request.top_k,
            filter_tag=request.filter_tag,
            score_threshold=request.score_threshold,
            collection_name=request.collection_name,
        )

        # Format and return results
        # Assuming search_results is a list of ScoredPoint or similar objects
        # Need to adapt this based on the actual structure of search_results from QdrantStore

        # Check if search_results is None or empty, which can happen if an error occurred in search_vector
        # or if no results were found.
        if search_results is None:
            # This case might indicate an issue within search_vector if it's not supposed to return None
            # For now, treat as no results found or an internal error not propagated as an exception.
            logger.warning(f"Search for query '{request.query_text[:50]}...' returned None. Assuming no results.")
            results_to_return = []
            count = 0
        else:
            results_to_return = [
                SemanticSearchResultItem(
                    id=point.id,
                    score=point.score,  # Ensure score is directly accessible
                    payload=point.payload if point.payload else {},
                )
                for point in search_results
            ]
            count = len(results_to_return)

        return SemanticSearchResponse(status="ok", count=count, results=results_to_return)

    except openai.APIError as oe:
        logger.error(f"OpenAI API error during semantic search for query '{request.query_text[:50]}...': {oe}")
        # It's important to return a proper HTTP error response to the client
        raise HTTPException(status_code=503, detail=f"OpenAI service unavailable: {str(oe)}")
    except HTTPException:  # Re-raise HTTPExceptions to let FastAPI handle them
        raise
    except Exception as e:
        # Log the full traceback for unexpected errors
        logger.exception(f"Unexpected error during semantic search for query '{request.query_text[:50]}...': {e}")
        # Return a generic 500 error to the client
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/clear_embeddings", response_model=ClearEmbeddingsResponse)
async def clear_embeddings_handler(
    # request: ClearEmbeddingsRequest, # No parameters for now, implies clear all
    qdrant_store: QdrantStore = Depends(get_qdrant_store),
):
    """
    Clears all embeddings (all vectors) from the Qdrant collection.
    This is a destructive operation.
    """
    try:
        # Using the existing purge_all_vectors method from QdrantStore
        # Note: purge_all_vectors in QdrantStore is async
        deleted_count = await qdrant_store.purge_all_vectors()
        logger.info(f"Successfully cleared {deleted_count} embeddings via /clear_embeddings.")
        return ClearEmbeddingsResponse(status="ok", deleted_count=deleted_count)
    except Exception as e:
        logger.error(f"Error clearing embeddings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear embeddings: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
