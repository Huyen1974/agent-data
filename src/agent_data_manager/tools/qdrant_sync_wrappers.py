"""Synchronous wrappers for Qdrant tools to enable MCP integration."""

import asyncio
import logging
from typing import Any

from .qdrant_embedding_tools import (
    qdrant_generate_and_store_embedding as async_qdrant_generate_and_store_embedding,
)
from .qdrant_embedding_tools import (
    qdrant_semantic_search as async_qdrant_semantic_search,
)
from .qdrant_embedding_tools import (
    semantic_search_qdrant as async_semantic_search_qdrant,
)
from .qdrant_vector_tools import (
    qdrant_delete_by_tag as async_qdrant_delete_by_tag,
)
from .qdrant_vector_tools import (
    qdrant_get_count as async_qdrant_get_count,
)
from .qdrant_vector_tools import (
    qdrant_health_check as async_qdrant_health_check,
)
from .qdrant_vector_tools import (
    qdrant_query_by_tag as async_qdrant_query_by_tag,
)
from .qdrant_vector_tools import (
    qdrant_upsert_vector as async_qdrant_upsert_vector,
)

logger = logging.getLogger(__name__)


def run_async_tool(async_func, *args, **kwargs):
    """Helper function to run async tools synchronously."""
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to create a new thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(*args, **kwargs))
                return future.result()
        else:
            # If no loop is running, we can use run_until_complete
            return loop.run_until_complete(async_func(*args, **kwargs))
    except RuntimeError:
        # If no event loop exists, create one
        return asyncio.run(async_func(*args, **kwargs))


def qdrant_health_check_sync() -> dict[str, Any]:
    """Synchronous wrapper for qdrant_health_check."""
    return run_async_tool(async_qdrant_health_check)


def qdrant_get_count_sync() -> dict[str, Any]:
    """Synchronous wrapper for qdrant_get_count."""
    return run_async_tool(async_qdrant_get_count)


def qdrant_upsert_vector_sync(
    vector_id: str,
    vector: list[float] | str,
    metadata: dict[str, Any] | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper for qdrant_upsert_vector."""
    return run_async_tool(async_qdrant_upsert_vector, vector_id, vector, metadata, tag)


def qdrant_query_by_tag_sync(
    tag: str,
    query_vector: list[float] | str | None = None,
    limit: int = 10,
    threshold: float = 0.0,
) -> dict[str, Any]:
    """Synchronous wrapper for qdrant_query_by_tag."""
    return run_async_tool(
        async_qdrant_query_by_tag, tag, query_vector, limit, threshold
    )


def qdrant_delete_by_tag_sync(tag: str) -> dict[str, Any]:
    """Synchronous wrapper for qdrant_delete_by_tag."""
    return run_async_tool(async_qdrant_delete_by_tag, tag)


def qdrant_semantic_search_sync(
    query_text: str, tag: str | None = None, limit: int = 10, threshold: float = 0.5
) -> dict[str, Any]:
    """Synchronous wrapper for qdrant_semantic_search."""
    return run_async_tool(
        async_qdrant_semantic_search, query_text, tag, limit, threshold
    )


def qdrant_generate_and_store_embedding_sync(
    vector_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    """Synchronous wrapper for qdrant_generate_and_store_embedding."""
    return run_async_tool(
        async_qdrant_generate_and_store_embedding, vector_id, text, metadata, tag
    )


def semantic_search_qdrant_sync(
    query_text: str,
    index_name: str | None = None,
    threshold: float = 0.5,
    top_n: int = 10,
) -> dict[str, Any]:
    """Synchronous wrapper for semantic_search_qdrant."""
    return run_async_tool(
        async_semantic_search_qdrant, query_text, index_name, threshold, top_n
    )
