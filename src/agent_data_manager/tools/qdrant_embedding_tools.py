"""Qdrant-based embedding tools for semantic search and analysis."""

import logging
import asyncio
from typing import Dict, List, Optional, Any

from ..config.settings import settings
from ..vector_store.qdrant_store import QdrantStore
from .external_tool_registry import get_openai_embedding, openai_client, OPENAI_AVAILABLE

logger = logging.getLogger(__name__)


def get_qdrant_store() -> QdrantStore:
    """Get or create QdrantStore instance."""
    config = settings.get_qdrant_config()
    return QdrantStore(
        url=config["url"],
        api_key=config["api_key"],
        collection_name=config["collection_name"],
        vector_size=config["vector_size"],
    )


async def qdrant_generate_and_store_embedding(
    vector_id: str, text: str, metadata: Optional[Dict[str, Any]] = None, tag: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate embedding for text and store in Qdrant.

    Args:
        vector_id: Unique identifier for the vector
        text: Text to generate embedding for
        metadata: Optional metadata dictionary
        tag: Optional tag for grouping vectors

    Returns:
        Result dictionary with operation status
    """
    if not openai_client or not OPENAI_AVAILABLE:
        return {"status": "failed", "error": "OpenAI client not available for embedding generation"}

    try:
        # Generate embedding using OpenAI
        # Note: get_openai_embedding might not be async, so handle both cases
        try:
            if asyncio.iscoroutinefunction(get_openai_embedding):
                embedding_result = await get_openai_embedding(agent_context=None, text_to_embed=text)
            else:
                embedding_result = get_openai_embedding(agent_context=None, text_to_embed=text)
        except TypeError:
            # Try without agent_context if the function doesn't accept it
            if asyncio.iscoroutinefunction(get_openai_embedding):
                embedding_result = await get_openai_embedding(text_to_embed=text)
            else:
                embedding_result = get_openai_embedding(text_to_embed=text)

        if "embedding" not in embedding_result or not embedding_result["embedding"]:
            return {
                "status": "failed",
                "error": f"Failed to generate embedding: {embedding_result.get('error', 'Unknown error')}",
            }

        embedding = embedding_result["embedding"]

        # Add text to metadata
        if metadata is None:
            metadata = {}
        metadata["original_text"] = text
        metadata["embedding_model"] = "text-embedding-3-small"  # Default model

        # Store in Qdrant
        store = get_qdrant_store()
        result = await store.upsert_vector(vector_id=vector_id, vector=embedding, metadata=metadata, tag=tag)

        return {
            "status": "success" if result.get("success") else "failed",
            "vector_id": vector_id,
            "text": text,
            "embedding_dimension": len(embedding),
            "result": result,
        }

    except Exception as e:
        logger.error(f"Failed to generate and store embedding for {vector_id}: {e}")
        return {"status": "failed", "error": str(e), "vector_id": vector_id}


async def qdrant_semantic_search(
    query_text: str, tag: Optional[str] = None, limit: int = 10, threshold: float = 0.5
) -> Dict[str, Any]:
    """
    Perform semantic search using Qdrant with OpenAI embeddings.

    Args:
        query_text: Text to search for semantically similar content
        tag: Optional tag to filter results
        limit: Maximum number of results
        threshold: Minimum similarity threshold

    Returns:
        Dictionary with search results
    """
    if not openai_client or not OPENAI_AVAILABLE:
        return {"status": "failed", "error": "OpenAI client not available for embedding generation"}

    try:
        # Generate query embedding
        try:
            if asyncio.iscoroutinefunction(get_openai_embedding):
                embedding_result = await get_openai_embedding(agent_context=None, text_to_embed=query_text)
            else:
                embedding_result = get_openai_embedding(agent_context=None, text_to_embed=query_text)
        except TypeError:
            # Try without agent_context if the function doesn't accept it
            if asyncio.iscoroutinefunction(get_openai_embedding):
                embedding_result = await get_openai_embedding(text_to_embed=query_text)
            else:
                embedding_result = get_openai_embedding(text_to_embed=query_text)

        if "embedding" not in embedding_result or not embedding_result["embedding"]:
            return {
                "status": "failed",
                "error": f"Failed to generate query embedding: {embedding_result.get('error', 'Unknown error')}",
            }

        query_embedding = embedding_result["embedding"]

        # Search in Qdrant
        store = get_qdrant_store()
        if tag:
            # Search with tag filter
            results = await store.query_vectors_by_tag(
                tag=tag, query_vector=query_embedding, limit=limit, threshold=threshold
            )
        else:
            # Search all vectors (need to implement this in QdrantStore)
            # For now, use a dummy tag search that returns all
            results = await store.query_vectors_by_tag(
                tag="",  # Empty tag - this won't work, need to fix QdrantStore
                query_vector=query_embedding,
                limit=limit,
                threshold=threshold,
            )

        # Format results for compatibility
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "id": result["id"],
                    "score": result["score"],
                    "similarity": result["score"],  # Alias for compatibility
                    "text": result["metadata"].get("original_text", ""),
                    "metadata": result["metadata"],
                }
            )

        return {
            "status": "success",
            "query": query_text,
            "results": formatted_results,
            "count": len(formatted_results),
            "tag": tag,
        }

    except Exception as e:
        logger.error(f"Failed to perform semantic search for '{query_text}': {e}")
        return {"status": "failed", "error": str(e), "query": query_text, "results": []}


async def qdrant_batch_generate_embeddings(
    texts: List[str], tag: Optional[str] = None, metadata_list: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate embeddings for multiple texts and store in Qdrant.

    Args:
        texts: List of texts to generate embeddings for
        tag: Optional tag for all vectors
        metadata_list: Optional list of metadata dicts (same length as texts)

    Returns:
        Result dictionary with batch operation status
    """
    if not openai_client or not OPENAI_AVAILABLE:
        return {"status": "failed", "error": "OpenAI client not available for embedding generation"}

    if metadata_list and len(metadata_list) != len(texts):
        return {"status": "failed", "error": "metadata_list length must match texts length"}

    try:
        results = []
        store = get_qdrant_store()

        for i, text in enumerate(texts):
            # Generate unique ID
            vector_id = f"batch_{i}_{hash(text)}"

            # Get metadata for this text
            metadata = metadata_list[i] if metadata_list else {}

            # Generate and store embedding
            result = await qdrant_generate_and_store_embedding(
                vector_id=vector_id, text=text, metadata=metadata, tag=tag
            )

            results.append({"index": i, "vector_id": vector_id, "text": text, "result": result})

        successful = sum(1 for r in results if r["result"]["status"] == "success")
        failed = len(results) - successful

        return {
            "status": "success",
            "processed": len(texts),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Failed to batch generate embeddings: {e}")
        return {"status": "failed", "error": str(e), "processed": 0, "results": []}


async def qdrant_similarity_search_by_id(
    vector_id: str, limit: int = 10, threshold: float = 0.5, tag: Optional[str] = None
) -> Dict[str, Any]:
    """
    Find vectors similar to an existing vector by its ID.

    Args:
        vector_id: ID of the vector to use as query
        limit: Maximum number of results
        threshold: Minimum similarity threshold
        tag: Optional tag to filter results

    Returns:
        Dictionary with similarity search results
    """
    try:
        # First, get the vector by ID (this would need to be implemented in QdrantStore)
        # For now, we'll return an error
        return {
            "status": "failed",
            "error": "Vector similarity search by ID not yet implemented in QdrantStore",
            "vector_id": vector_id,
        }

    except Exception as e:
        logger.error(f"Failed to perform similarity search for vector {vector_id}: {e}")
        return {"status": "failed", "error": str(e), "vector_id": vector_id, "results": []}


# Compatibility aliases for FAISS replacement
async def semantic_search_qdrant(
    query_text: str,
    index_name: Optional[str] = None,  # Ignored, using default collection
    threshold: float = 0.5,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Compatibility wrapper for FAISS semantic_search_cosine replacement.

    Args:
        query_text: Text to search for
        index_name: Ignored (for FAISS compatibility)
        threshold: Similarity threshold
        top_n: Maximum results

    Returns:
        Search results in FAISS-compatible format
    """
    result = await qdrant_semantic_search(query_text=query_text, limit=top_n, threshold=threshold)

    if result["status"] == "success":
        # Convert to FAISS-compatible format
        similar_items = []
        for item in result["results"]:
            similar_items.append(
                {"key": item["id"], "similarity": item["score"], "content": item["text"], "metadata": item["metadata"]}
            )

        return {"status": "success", "similar_items": similar_items}
    else:
        return {"status": "failed", "error": result["error"], "similar_items": []}
