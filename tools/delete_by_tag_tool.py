import logging
from typing import Dict, Any
import asyncio

from agent_data.vector_store.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


async def delete_by_tag(tag: str) -> Dict[str, Any]:
    """
    Delete vectors from the Qdrant collection by a specific tag.

    Args:
        tag: The tag to filter by for deletion.

    Returns:
        A dictionary with status and count of deleted vectors.
    """
    if not tag or not tag.strip():
        return {"status": "failed", "error": "Tag cannot be empty or whitespace only.", "deleted_count": 0}

    try:
        # Get the QdrantStore instance
        qdrant_store = QdrantStore()

        # Call the delete_vectors_by_tag method
        deleted_count = await qdrant_store.delete_vectors_by_tag(tag=tag.strip())

        logger.info(f"Successfully deleted {deleted_count} vectors with tag '{tag}'")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} vectors with tag '{tag}'",
        }

    except Exception as e:
        logger.error(f"Error deleting vectors by tag '{tag}': {e}", exc_info=True)
        return {"status": "failed", "error": f"Failed to delete vectors by tag '{tag}': {str(e)}", "deleted_count": 0}


# Synchronous wrapper for compatibility with the tool registration system
def delete_by_tag_sync(tag: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for delete_by_tag function.

    Args:
        tag: The tag to filter by for deletion.

    Returns:
        A dictionary with status and count of deleted vectors.
    """
    try:
        # Run the async function in the current event loop or create a new one
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, we need to handle this differently
            # For now, we'll create a new event loop in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, delete_by_tag(tag))
                return future.result()
        else:
            return loop.run_until_complete(delete_by_tag(tag))
    except Exception as e:
        logger.error(f"Error in synchronous wrapper for delete_by_tag: {e}", exc_info=True)
        return {"status": "failed", "error": f"Failed to delete vectors by tag '{tag}': {str(e)}", "deleted_count": 0}


# Example usage (for testing purposes)
if __name__ == "__main__":
    # Test the delete_by_tag function
    test_tag = "test_tag_to_delete"
    print(f"Testing delete_by_tag with tag: {test_tag}")

    try:
        result = delete_by_tag_sync(test_tag)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error during test: {e}")
