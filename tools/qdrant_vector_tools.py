"""QdrantStore tools for Agent Data system integration."""

import logging
from typing import Dict, List, Optional, Any, Union
import numpy as np

from ..config.settings import settings
from ..vector_store.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)

# Global QdrantStore instance for tool operations
_qdrant_store = None


def get_qdrant_store() -> QdrantStore:
    """Get or create QdrantStore instance."""
    global _qdrant_store
    if _qdrant_store is None:
        config = settings.get_qdrant_config()
        _qdrant_store = QdrantStore(
            url=config["url"],
            api_key=config["api_key"],
            collection_name=config["collection_name"],
            vector_size=config["vector_size"],
        )
    return _qdrant_store


async def qdrant_upsert_vector(
    vector_id: str,
    vector: Union[List[float], str],
    metadata: Optional[Dict[str, Any]] = None,
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upsert a vector to Qdrant store.

    Args:
        vector_id: Unique identifier for the vector
        vector: Vector data as list of floats or comma-separated string
        metadata: Optional metadata dictionary
        tag: Optional tag for grouping vectors

    Returns:
        Result dictionary with operation status
    """
    try:
        # Handle string input (comma-separated values)
        if isinstance(vector, str):
            vector = [float(x.strip()) for x in vector.split(",")]

        # Validate vector
        if not isinstance(vector, (list, np.ndarray)):
            return {"status": "failed", "error": f"Vector must be a list or numpy array, got {type(vector)}"}

        store = get_qdrant_store()
        result = await store.upsert_vector(vector_id=vector_id, vector=vector, metadata=metadata, tag=tag)

        return {"status": "success" if result.get("success") else "failed", "vector_id": vector_id, "result": result}

    except Exception as e:
        logger.error(f"Failed to upsert vector {vector_id}: {e}")
        return {"status": "failed", "error": str(e), "vector_id": vector_id}


async def qdrant_query_by_tag(
    tag: str, query_vector: Optional[Union[List[float], str]] = None, limit: int = 10, threshold: float = 0.0
) -> Dict[str, Any]:
    """
    Query vectors by tag with optional similarity search.

    Args:
        tag: Tag to filter vectors
        query_vector: Optional vector for similarity search
        limit: Maximum number of results
        threshold: Minimum similarity threshold

    Returns:
        Dictionary with search results
    """
    try:
        # Handle string input for query vector
        if isinstance(query_vector, str):
            query_vector = [float(x.strip()) for x in query_vector.split(",")]

        store = get_qdrant_store()
        results = await store.query_vectors_by_tag(tag=tag, query_vector=query_vector, limit=limit, threshold=threshold)

        return {"status": "success", "tag": tag, "results": results, "count": len(results)}

    except Exception as e:
        logger.error(f"Failed to query vectors by tag {tag}: {e}")
        return {"status": "failed", "error": str(e), "tag": tag, "results": []}


async def qdrant_delete_by_tag(tag: str) -> Dict[str, Any]:
    """
    Delete all vectors with a specific tag.

    Args:
        tag: Tag identifying vectors to delete

    Returns:
        Result dictionary with deletion status
    """
    try:
        store = get_qdrant_store()
        result = await store.delete_vectors_by_tag(tag)

        return {"status": "success" if result.get("success") else "failed", "tag": tag, "result": result}

    except Exception as e:
        logger.error(f"Failed to delete vectors by tag {tag}: {e}")
        return {"status": "failed", "error": str(e), "tag": tag}


async def qdrant_get_count() -> Dict[str, Any]:
    """
    Get total number of vectors in the store.

    Returns:
        Dictionary with vector count
    """
    try:
        store = get_qdrant_store()
        count = await store.get_vector_count()

        return {"status": "success", "count": count}

    except Exception as e:
        logger.error(f"Failed to get vector count: {e}")
        return {"status": "failed", "error": str(e), "count": 0}


async def qdrant_health_check() -> Dict[str, Any]:
    """
    Check if Qdrant store is healthy and accessible.

    Returns:
        Dictionary with health status
    """
    try:
        store = get_qdrant_store()
        healthy = await store.health_check()

        return {
            "status": "success",
            "healthy": healthy,
            "message": "Qdrant store is accessible" if healthy else "Qdrant store is not accessible",
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "failed", "healthy": False, "error": str(e)}


# Tool function aliases for backward compatibility
async def save_vector_to_qdrant(
    vector_id: str,
    vector: Union[List[float], str],
    metadata: Optional[Dict[str, Any]] = None,
    tag: Optional[str] = None,
) -> Dict[str, Any]:
    """Alias for qdrant_upsert_vector for backward compatibility."""
    return await qdrant_upsert_vector(vector_id, vector, metadata, tag)


async def search_vectors_qdrant(
    tag: str, query_vector: Optional[Union[List[float], str]] = None, limit: int = 10, threshold: float = 0.0
) -> Dict[str, Any]:
    """Alias for qdrant_query_by_tag for backward compatibility."""
    return await qdrant_query_by_tag(tag, query_vector, limit, threshold)
