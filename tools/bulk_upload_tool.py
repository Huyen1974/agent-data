import asyncio
import logging
from typing import Any

from qdrant_client.http.models import PointStruct

from agent_data.vector_store.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


async def bulk_upload(
    collection_name: str, points: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Upload multiple vectors to a Qdrant collection efficiently.

    Args:
        collection_name: The name of the collection to upload to.
        points: A list of dictionaries, each containing 'vector' and 'payload' keys.
                Optionally, each point can have an 'id' key. If not provided,
                sequential IDs starting from 1 will be assigned.

    Returns:
        A dictionary with status and count of uploaded vectors.
    """
    if not collection_name or not collection_name.strip():
        return {
            "status": "failed",
            "error": "Collection name cannot be empty or whitespace only.",
            "uploaded_count": 0,
        }

    if not points or not isinstance(points, list):
        return {
            "status": "failed",
            "error": "Points must be a non-empty list.",
            "uploaded_count": 0,
        }

    try:
        # Get the QdrantStore instance
        qdrant_store = QdrantStore()

        # Format points for Qdrant
        formatted_points = []
        for i, point in enumerate(points):
            if not isinstance(point, dict):
                logger.warning(f"Skipping invalid point at index {i}: not a dictionary")
                continue

            if "vector" not in point:
                logger.warning(f"Skipping point at index {i}: missing 'vector' key")
                continue

            # Use provided ID or generate sequential ID
            point_id = point.get("id", i + 1)
            vector = point["vector"]
            payload = point.get("payload", {})

            formatted_points.append(
                PointStruct(id=point_id, vector=vector, payload=payload)
            )

        if not formatted_points:
            return {
                "status": "failed",
                "error": "No valid points found to upload.",
                "uploaded_count": 0,
            }

        # Use the client's upsert method for batch uploading
        result = qdrant_store.client.upsert(
            collection_name=collection_name.strip(), points=formatted_points
        )

        logger.info(
            f"Successfully uploaded {len(formatted_points)} points to collection '{collection_name}'"
        )

        return {
            "status": "success",
            "uploaded_count": len(formatted_points),
            "message": f"Uploaded {len(formatted_points)} points to collection '{collection_name}'",
            "operation_id": (
                result.operation_id if hasattr(result, "operation_id") else None
            ),
        }

    except Exception as e:
        logger.error(
            f"Error bulk uploading to collection '{collection_name}': {e}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "error": f"Failed to bulk upload to collection '{collection_name}': {str(e)}",
            "uploaded_count": 0,
        }


# Synchronous wrapper for compatibility with the tool registration system
def bulk_upload_sync(
    collection_name: str, points: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Synchronous wrapper for bulk_upload function.

    Args:
        collection_name: The name of the collection to upload to.
        points: A list of dictionaries, each containing 'vector' and 'payload' keys.

    Returns:
        A dictionary with status and count of uploaded vectors.
    """
    try:
        # Run the async function in the current event loop or create a new one
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to handle this differently
            # For now, we'll create a new event loop in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, bulk_upload(collection_name, points)
                )
                return future.result()
        else:
            return loop.run_until_complete(bulk_upload(collection_name, points))
    except Exception as e:
        logger.error(
            f"Error in synchronous wrapper for bulk_upload: {e}", exc_info=True
        )
        return {
            "status": "failed",
            "error": f"Failed to bulk upload to collection '{collection_name}': {str(e)}",
            "uploaded_count": 0,
        }


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Test the bulk_upload function
    test_collection = "test_collection"
    test_points = [
        {
            "id": 1,
            "vector": [0.1] * 1536,
            "payload": {"tag": "test1", "content": "First test point"},
        },
        {
            "id": 2,
            "vector": [0.2] * 1536,
            "payload": {"tag": "test2", "content": "Second test point"},
        },
    ]

    print(f"Testing bulk_upload with collection: {test_collection}")

    try:
        result = bulk_upload_sync(test_collection, test_points)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error during test: {e}")
