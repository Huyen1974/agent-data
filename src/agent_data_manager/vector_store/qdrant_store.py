"""Qdrant implementation of VectorStore interface."""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition

from .base import VectorStore

logger = logging.getLogger(__name__)

# Initialize API key masking for this module
try:
    from ..tools.api_key_middleware import setup_api_key_masking, mask_config_dict

    setup_api_key_masking(__name__)
except ImportError:
    # Fallback function if middleware is not available
    def mask_config_dict(config):
        masked = config.copy()
        if "api_key" in masked:
            masked["api_key"] = "***MASKED***"
        return masked


# Initialize metrics integration
try:
    from ..tools.prometheus_metrics import (
        MetricsTimer,
        record_qdrant_error,
        update_qdrant_connection_status,
        update_vector_count,
        record_semantic_search,
        initialize_metrics_pusher,
    )

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Prometheus metrics not available")

    # Mock functions if metrics not available
    class MetricsTimer:
        def __init__(self, operation: str):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    def record_qdrant_error(error_type: str):
        pass

    def update_qdrant_connection_status(connected: bool):
        pass

    def update_vector_count(collection: str, count: int):
        pass

    def record_semantic_search():
        pass

    def initialize_metrics_pusher(pushgateway_url: Optional[str] = None, push_interval: int = 60):
        pass


class QdrantStore(VectorStore):
    """Qdrant implementation of VectorStore interface."""

    def __init__(
        self,
        url: str,
        api_key: str,
        collection_name: str = "agent_data_vectors",
        vector_size: int = 1536,  # Default OpenAI embedding size
        distance: Distance = Distance.COSINE,
    ):
        """
        Initialize Qdrant vector store.

        Args:
            url: Qdrant cluster URL
            api_key: Qdrant API key
            collection_name: Name of the collection to use
            vector_size: Dimension of vectors
            distance: Distance metric for similarity
        """
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance = distance
        self._client = None
        self._collection_initialized = False

        # Initialize metrics pusher if enabled
        if METRICS_AVAILABLE:
            try:
                from ..config.settings import settings

                metrics_config = settings.get_metrics_config()
                if metrics_config.get("enabled", True):
                    initialize_metrics_pusher(
                        pushgateway_url=metrics_config.get("pushgateway_url"),
                        push_interval=metrics_config.get("push_interval", 60),
                    )
                    logger.info("Metrics pusher initialized for QdrantStore")
            except Exception as e:
                logger.warning(f"Failed to initialize metrics pusher: {e}")

    @property
    def client(self) -> QdrantClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(url=self.url, api_key=self.api_key, timeout=30.0)
        return self._client

    async def _ensure_collection(self) -> None:
        """Ensure the collection exists with proper configuration."""
        if self._collection_initialized:
            return

        try:
            # Check if collection exists
            collections = await asyncio.to_thread(self.client.get_collections)
            collection_names = [col.name for col in collections.collections]

            if self.collection_name not in collection_names:
                # Create collection
                await asyncio.to_thread(
                    self.client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.vector_size, distance=self.distance),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")

            # Ensure payload index for 'tag' field exists
            try:
                await asyncio.to_thread(
                    self.client.create_payload_index,
                    collection_name=self.collection_name,
                    field_name="tag",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                logger.info(
                    f"Ensured payload index for field 'tag' (type KEYWORD) in collection '{self.collection_name}'."
                )
            except Exception as e:
                # Log error if index creation fails for unexpected reasons.
                # Qdrant might also raise specific exceptions for conflicts if an incompatible index exists.
                logger.error(
                    f"Failed to ensure payload index for 'tag' field: {e}. Filtering may fail or be inefficient."
                )

            self._collection_initialized = True

        except Exception as e:
            logger.error(f"Failed to ensure collection {self.collection_name}: {e}")
            raise

    async def upsert_vector(
        self,
        vector_id: str,
        vector: Union[List[float], np.ndarray],
        metadata: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a vector with metadata."""
        await self._ensure_collection()

        with MetricsTimer("upsert"):
            try:
                # Convert vector to list if numpy array
                if isinstance(vector, np.ndarray):
                    vector = vector.tolist()

                # Prepare payload with metadata and tag
                payload = metadata.copy() if metadata else {}
                if tag:
                    payload["tag"] = tag

                # Store original vector_id in payload for reference
                payload["doc_id"] = vector_id

                # Generate a valid UUID for Qdrant point ID
                point_id = str(uuid.uuid4())

                # Create point
                point = PointStruct(id=point_id, vector=vector, payload=payload)

                # Upsert the point
                result = await asyncio.to_thread(
                    self.client.upsert, collection_name=self.collection_name, points=[point]
                )

                # Update connection status on successful operation
                update_qdrant_connection_status(True)

                return {
                    "success": True,
                    "vector_id": vector_id,  # Return original doc_id for compatibility
                    "point_id": point_id,  # Include Qdrant point ID for reference
                    "operation_id": result.operation_id if hasattr(result, "operation_id") else None,
                }

            except Exception as e:
                logger.error(f"Failed to upsert vector {vector_id}: {e}")
                record_qdrant_error("upsert")
                update_qdrant_connection_status(False)
                return {"success": False, "error": str(e), "vector_id": vector_id}

    async def query_vectors_by_tag(
        self,
        tag: str,
        query_vector: Optional[Union[List[float], np.ndarray]] = None,
        limit: int = 10,
        threshold: float = 0.0,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query vectors by tag with optional similarity search."""
        await self._ensure_collection()

        with MetricsTimer("query_by_tag"):
            try:
                # Record semantic search if query vector is provided
                if query_vector is not None:
                    record_semantic_search()

                # Create filter for tag
                query_filter = Filter(must=[FieldCondition(key="tag", match=models.MatchValue(value=tag))])

                if query_vector is not None:
                    # Convert vector to list if numpy array
                    if isinstance(query_vector, np.ndarray):
                        query_vector = query_vector.tolist()

                    # Perform similarity search
                    results = await asyncio.to_thread(
                        self.client.search,
                        collection_name=self.collection_name,
                        query_vector=query_vector,
                        query_filter=query_filter,
                        limit=limit,
                        score_threshold=threshold,
                    )
                else:
                    # Just get vectors with the tag (no similarity search)
                    results = await asyncio.to_thread(
                        self.client.scroll,
                        collection_name=self.collection_name,
                        scroll_filter=query_filter,
                        limit=limit,
                    )
                    # For scroll results, we need to extract points
                    if hasattr(results, "points"):
                        points = results.points
                    else:
                        points = results[0]  # scroll returns (points, next_page_offset)

                    # Convert scroll results to search-like format
                    results = []
                    for point in points:
                        results.append(
                            type(
                                "ScoredPoint",
                                (),
                                {
                                    "id": point.id,
                                    "score": 1.0,  # No similarity score for scroll
                                    "payload": point.payload,
                                    "vector": point.vector,
                                },
                            )()
                        )

                # Format results
                formatted_results = []
                for point in results:
                    result_dict = {
                        "id": point.id,
                        "score": getattr(point, "score", 1.0),
                        "metadata": point.payload,
                        "vector": getattr(point, "vector", None),
                    }
                    formatted_results.append(result_dict)

                # Update connection status on successful operation
                update_qdrant_connection_status(True)

                return {"results": formatted_results, "total": len(formatted_results)}

            except Exception as e:
                logger.error(f"Failed to query vectors by tag {tag}: {e}")
                record_qdrant_error("query")
                update_qdrant_connection_status(False)
                return {"results": [], "total": 0}

    async def semantic_search(
        self,
        query_text: str,
        limit: int = 10,
        tag: Optional[str] = None,
        score_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Perform semantic search using OpenAI embeddings.

        Args:
            query_text: Text to search for semantically similar content
            limit: Maximum number of results
            tag: Optional tag to filter results
            score_threshold: Minimum similarity threshold

        Returns:
            Dictionary with search results
        """
        await self._ensure_collection()

        try:
            # Import the get_openai_embedding function
            from ..tools.external_tool_registry import get_openai_embedding

            # Generate embedding for the query text
            embedding_result = await get_openai_embedding(agent_context=None, text_to_embed=query_text)
            if "embedding" not in embedding_result or not embedding_result["embedding"]:
                logger.error(f"Failed to generate embedding for query: {query_text}")
                return {
                    "status": "failed",
                    "error": "Failed to generate embedding for query",
                    "query": query_text,
                    "results": [],
                }

            query_vector = embedding_result["embedding"]

            # Create filter for tag if specified
            search_filter = None
            if tag:
                search_filter = Filter(must=[FieldCondition(key="tag", match=models.MatchValue(value=tag))])

            # Perform vector search
            with MetricsTimer("semantic_search"):
                results = await asyncio.to_thread(
                    self.client.search,
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    query_filter=search_filter,
                    limit=limit,
                    score_threshold=score_threshold,
                )

                # Update metrics
                record_semantic_search()
                update_qdrant_connection_status(True)

                # Format results
                formatted_results = []
                for point in results:
                    result_dict = {
                        "id": point.id,
                        "score": point.score,
                        "metadata": point.payload,
                        "vector": getattr(point, "vector", None),
                    }
                    formatted_results.append(result_dict)

                return {
                    "status": "success",
                    "query": query_text,
                    "results": formatted_results,
                    "count": len(formatted_results),
                    "tag": tag,
                }

        except Exception as e:
            logger.error(f"Failed to perform semantic search for '{query_text}': {e}")
            record_qdrant_error("semantic_search")
            update_qdrant_connection_status(False)
            return {"status": "failed", "error": str(e), "query": query_text, "results": []}

    async def get_recent_documents(self, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        Get recent documents from the collection.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Dictionary with recent documents
        """
        await self._ensure_collection()

        with MetricsTimer("get_recent"):
            try:
                # Use scroll to get recent documents (without filter)
                results = await asyncio.to_thread(
                    self.client.scroll,
                    collection_name=self.collection_name,
                    limit=limit,
                    offset=offset,
                )

                # For scroll results, we need to extract points
                if hasattr(results, "points"):
                    points = results.points
                else:
                    points = results[0]  # scroll returns (points, next_page_offset)

                # Format results
                formatted_results = []
                for point in points:
                    result_dict = {
                        "id": point.id,
                        "score": 1.0,  # No similarity score for scroll
                        "metadata": point.payload,
                        "vector": getattr(point, "vector", None),
                    }
                    formatted_results.append(result_dict)

                # Update connection status on successful operation
                update_qdrant_connection_status(True)

                return {"results": formatted_results, "total": len(formatted_results)}

            except Exception as e:
                logger.error(f"Failed to get recent documents: {e}")
                record_qdrant_error("get_recent")
                update_qdrant_connection_status(False)
                return {"results": [], "total": 0}

    async def delete_vectors_by_tag(self, tag: str) -> Dict[str, Any]:
        """Delete all vectors with a specific tag."""
        await self._ensure_collection()

        try:
            # Create filter for tag
            delete_filter = Filter(must=[FieldCondition(key="tag", match=models.MatchValue(value=tag))])

            # Delete points with the tag
            result = await asyncio.to_thread(
                self.client.delete,
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(filter=delete_filter),
            )

            return {
                "success": True,
                "tag": tag,
                "operation_id": result.operation_id if hasattr(result, "operation_id") else None,
            }

        except Exception as e:
            logger.error(f"Failed to delete vectors by tag {tag}: {e}")
            return {"success": False, "error": str(e), "tag": tag}

    async def get_vector_count(self) -> int:
        """Get total number of vectors stored."""
        await self._ensure_collection()

        with MetricsTimer("get_count"):
            try:
                info = await asyncio.to_thread(self.client.get_collection, collection_name=self.collection_name)
                count = info.vectors_count or 0

                # Update vector count metric
                update_vector_count(self.collection_name, count)
                update_qdrant_connection_status(True)

                return count

            except Exception as e:
                logger.error(f"Failed to get vector count: {e}")
                record_qdrant_error("get_count")
                update_qdrant_connection_status(False)
                return 0

    async def health_check(self) -> bool:
        """Check if the vector store is healthy and accessible."""
        with MetricsTimer("health_check"):
            try:
                # Try to get collections as a health check
                await asyncio.to_thread(self.client.get_collections)
                update_qdrant_connection_status(True)
                return True

            except Exception as e:
                logger.error(f"Qdrant health check failed: {e}")
                record_qdrant_error("health_check")
                update_qdrant_connection_status(False)
                return False

    def close(self) -> None:
        """Close the Qdrant client connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._collection_initialized = False
