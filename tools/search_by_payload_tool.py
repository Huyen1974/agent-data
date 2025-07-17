import asyncio
import logging
from typing import Any

from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from agent_data.vector_store.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


async def search_by_payload(
    collection_name: str | None = None,
    field: str = "tag",
    value: Any = None,
    limit: int = 10,
    offset: int | str | None = None,
    with_payload: bool = True,
    with_vectors: bool = False,
) -> dict[str, Any]:
    """
    Search for points in the Qdrant collection by payload fields.

    Args:
        collection_name: Optional name of the collection to search in. Defaults to QdrantStore's default collection.
        field: The payload field to search by (e.g., 'tag', 'content', 'source').
        value: The value to match in the specified field.
        limit: Maximum number of results to return (default: 10).
        offset: Optional offset for pagination (Qdrant's next_page_offset).
        with_payload: Whether to include payload in results (default: True).
        with_vectors: Whether to include vectors in results (default: False).

    Returns:
        A dictionary with status, results, count, and next_offset.
    """
    if not field or not field.strip():
        return {
            "status": "failed",
            "error": "Field cannot be empty or whitespace only.",
            "results": [],
            "count": 0,
            "next_offset": None,
        }

    if value is None:
        return {
            "status": "failed",
            "error": "Value cannot be None.",
            "results": [],
            "count": 0,
            "next_offset": None,
        }

    try:
        # Get the QdrantStore instance
        qdrant_store = QdrantStore()

        # Use the collection name from QdrantStore if not provided
        target_collection = (
            collection_name if collection_name else qdrant_store.collection_name
        )

        # Create filter for the specified field and value
        search_filter = Filter(
            must=[FieldCondition(key=field.strip(), match=MatchValue(value=value))]
        )

        logger.info(
            f"Searching in collection '{target_collection}' for field '{field}' with value '{value}'"
        )

        # Use scroll to search by payload (more efficient for payload-only searches)
        results, next_page_offset = qdrant_store.client.scroll(
            collection_name=target_collection,
            scroll_filter=search_filter,
            limit=limit,
            offset=offset,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )

        # Convert results to a more readable format
        formatted_results = []
        for point in results:
            result_item = {
                "id": point.id,
                "payload": point.payload if with_payload else None,
                "vector": point.vector if with_vectors else None,
            }
            formatted_results.append(result_item)

        logger.info(
            f"Found {len(formatted_results)} points matching field '{field}' with value '{value}'"
        )

        return {
            "status": "success",
            "results": formatted_results,
            "count": len(formatted_results),
            "next_offset": next_page_offset,
            "message": f"Found {len(formatted_results)} points with {field}='{value}'",
        }

    except Exception as e:
        logger.error(
            f"Error searching by payload field '{field}' with value '{value}': {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": f"Failed to search by payload: {str(e)}",
            "results": [],
            "count": 0,
            "next_offset": None,
        }


# Synchronous wrapper for compatibility with the tool registration system
def search_by_payload_sync(
    collection_name: str | None = None,
    field: str = "tag",
    value: Any = None,
    limit: int = 10,
    offset: int | str | None = None,
    with_payload: bool = True,
    with_vectors: bool = False,
) -> dict[str, Any]:
    """
    Synchronous wrapper for search_by_payload function.

    Args:
        collection_name: Optional name of the collection to search in.
        field: The payload field to search by.
        value: The value to match in the specified field.
        limit: Maximum number of results to return.
        offset: Optional offset for pagination.
        with_payload: Whether to include payload in results.
        with_vectors: Whether to include vectors in results.

    Returns:
        A dictionary with status, results, count, and next_offset.
    """
    try:
        # Try to get the current event loop, but handle the case where it's closed or doesn't exist
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            # No event loop or it's closed, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If we're already in an async context, we need to handle this differently
            # For now, we'll create a new event loop in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    search_by_payload(
                        collection_name,
                        field,
                        value,
                        limit,
                        offset,
                        with_payload,
                        with_vectors,
                    ),
                )
                return future.result()
        else:
            return loop.run_until_complete(
                search_by_payload(
                    collection_name,
                    field,
                    value,
                    limit,
                    offset,
                    with_payload,
                    with_vectors,
                )
            )
    except Exception as e:
        logger.error(
            f"Error in synchronous wrapper for search_by_payload: {e}", exc_info=True
        )
        return {
            "status": "failed",
            "error": f"Failed to search by payload: {str(e)}",
            "results": [],
            "count": 0,
            "next_offset": None,
        }


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Test the search_by_payload function
    test_field = "tag"
    test_value = "test_tag"
    print(f"Testing search_by_payload with field: {test_field}, value: {test_value}")

    try:
        result = search_by_payload_sync(field=test_field, value=test_value, limit=5)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error during test: {e}")
