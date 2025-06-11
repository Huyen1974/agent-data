#!/usr/bin/env python3
"""
Test Qdrant Cloud connection and QdrantStore initialization.
This script diagnoses connection issues with Qdrant Cloud by testing:
1. QdrantStore initialization
2. Health check
3. Collection creation
4. Single vector upload and retrieval

Created for CLI 114B3 to diagnose hanging issues during migration.
"""

import os
import sys
import time
import asyncio
import logging
from datetime import datetime
from typing import Optional
import uuid

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_data.vector_store.qdrant_store import QdrantStore  # noqa: E402


def setup_logging() -> logging.Logger:
    """Set up logging for the connection test."""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, "qdrant_connection_test.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Starting Qdrant Connection Test - CLI 114B3")
    logger.info("=" * 80)

    return logger


def log_operation(logger: logging.Logger, action: str, status: str, duration_ms: int, details: str = ""):
    """Log operation in the required format: [timestamp] [Action] [Status] [Duration_ms]"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_msg = f"[{timestamp}] [{action}] [{status}] [{duration_ms}ms]"
    if details:
        log_msg += f" - {details}"
    logger.info(log_msg)


async def test_with_timeout(coro, timeout_seconds: int, operation_name: str):
    """Execute a coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"{operation_name} timed out after {timeout_seconds} seconds")


async def retry_operation(operation, max_retries: int, operation_name: str, logger: logging.Logger):
    """Retry an operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            result = await operation()
            duration_ms = int((time.time() - start_time) * 1000)
            log_operation(logger, operation_name, "SUCCESS", duration_ms)
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                log_operation(
                    logger,
                    operation_name,
                    "RETRY",
                    duration_ms,
                    f"Attempt {attempt + 1}/{max_retries}, error: {str(e)}, retrying in {wait_time}s",
                )
                await asyncio.sleep(wait_time)
            else:
                log_operation(logger, operation_name, "FAILED", duration_ms, f"Final attempt failed: {str(e)}")
                raise


async def test_qdrant_initialization(logger: logging.Logger) -> Optional[QdrantStore]:
    """Test QdrantStore initialization."""
    logger.info("Testing QdrantStore initialization...")

    # Set required environment variables
    qdrant_url = "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io"
    api_key = os.getenv("QDRANT_API_KEY")

    if not api_key:
        log_operation(logger, "INIT_CHECK", "FAILED", 0, "QDRANT_API_KEY not set")
        return None

    # Set environment variables for QdrantStore
    os.environ["QDRANT_URL"] = qdrant_url
    os.environ["QDRANT_COLLECTION_NAME"] = "test_connection_collection"

    logger.info("Qdrant URL: %s", qdrant_url)
    logger.info("API Key: %s...", api_key[:20])
    logger.info("Collection: test_connection_collection")

    async def init_store():
        return QdrantStore()

    try:
        store = await retry_operation(
            lambda: test_with_timeout(init_store(), 30, "QdrantStore initialization"),
            max_retries=3,
            operation_name="INIT_STORE",
            logger=logger,
        )
        return store
    except Exception as e:
        logger.error("Failed to initialize QdrantStore: %s", e)
        return None


async def test_health_check(store: QdrantStore, logger: logging.Logger) -> bool:
    """Test Qdrant health check."""
    logger.info("Testing Qdrant health check...")

    # Check if health_check method exists
    if not hasattr(store, "health_check"):
        log_operation(logger, "HEALTH_CHECK", "FAILED", 0, "health_check method not found in QdrantStore")
        return False

    async def health_check():
        # Try to get collections as a health check (similar to ADK implementation)
        try:
            await asyncio.to_thread(store.client.get_collections)
            return True
        except Exception as e:
            logger.error("Health check failed: %s", e)
            return False

    try:
        result = await retry_operation(
            lambda: test_with_timeout(health_check(), 30, "Health check"),
            max_retries=3,
            operation_name="HEALTH_CHECK",
            logger=logger,
        )
        return result
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return False


async def test_collection_operations(store: QdrantStore, logger: logging.Logger) -> bool:
    """Test collection creation and basic operations."""
    logger.info("Testing collection operations...")

    async def check_collection():
        # Check if collection exists
        collection_exists = await asyncio.to_thread(
            store.client.collection_exists, collection_name=store.collection_name
        )
        return collection_exists

    try:
        exists = await retry_operation(
            lambda: test_with_timeout(check_collection(), 30, "Collection check"),
            max_retries=3,
            operation_name="CHECK_COLLECTION",
            logger=logger,
        )

        if exists:
            logger.info("Collection '%s' already exists", store.collection_name)
        else:
            logger.info(
                "Collection '%s' does not exist, it should be created during initialization", store.collection_name
            )

        return True
    except Exception as e:
        logger.error("Collection operations failed: %s", e)
        return False


async def test_vector_operations(store: QdrantStore, logger: logging.Logger) -> bool:
    """Test single vector upload and retrieval."""
    logger.info("Testing vector upload and retrieval...")

    # Generate test vector
    test_vector = [0.1] * 1536  # 1536-dimensional vector with all 0.1 values
    test_id = str(uuid.uuid4())
    test_metadata = {"tag": "test_connection", "test_type": "connection_test", "timestamp": datetime.now().isoformat()}

    # Test vector upload
    async def upload_vector():
        return await store.upsert_vector(test_id, test_vector, test_metadata)

    try:
        upload_result = await retry_operation(
            lambda: test_with_timeout(upload_vector(), 30, "Vector upload"),
            max_retries=3,
            operation_name="UPLOAD_VECTOR",
            logger=logger,
        )

        if not upload_result:
            logger.error("Vector upload returned False")
            return False

        logger.info("Successfully uploaded test vector with ID: %s", test_id)
    except Exception as e:
        logger.error("Vector upload failed: %s", e)
        return False

    # Test vector retrieval
    async def retrieve_vector():
        return store.get_vector_by_id(test_id)

    try:
        retrieved = await retry_operation(
            lambda: test_with_timeout(retrieve_vector(), 30, "Vector retrieval"),
            max_retries=3,
            operation_name="RETRIEVE_VECTOR",
            logger=logger,
        )

        if retrieved is None:
            logger.error("Failed to retrieve vector with ID: %s", test_id)
            return False

        logger.info("Successfully retrieved test vector: %s", retrieved["id"])

        # Verify vector data
        if retrieved["vector"] == test_vector and retrieved["payload"]["tag"] == "test_connection":
            logger.info("Vector data verification successful")
        else:
            logger.warning("Vector data verification failed - data mismatch")

        return True
    except Exception as e:
        logger.error("Vector retrieval failed: %s", e)
        return False


async def cleanup_test_data(store: QdrantStore, logger: logging.Logger):
    """Clean up test data."""
    logger.info("Cleaning up test data...")

    async def delete_test_vectors():
        try:
            # Delete vectors with test tag
            deleted_count = await store.delete_vectors_by_tag("test_connection")
            return deleted_count
        except Exception as e:
            logger.error("Cleanup failed: %s", e)
            return 0

    try:
        deleted = await retry_operation(
            lambda: test_with_timeout(delete_test_vectors(), 30, "Cleanup"),
            max_retries=3,
            operation_name="CLEANUP",
            logger=logger,
        )
        logger.info("Cleanup completed: %s test vectors deleted", deleted)
    except Exception as e:
        logger.error("Cleanup failed: %s", e)


async def main():
    """Main test function."""
    logger = setup_logging()

    try:
        # Test 1: QdrantStore initialization
        store = await test_qdrant_initialization(logger)
        if not store:
            logger.error("❌ QdrantStore initialization failed - cannot proceed with further tests")
            return False

        logger.info("✅ QdrantStore initialization successful")

        # Test 2: Health check
        health_ok = await test_health_check(store, logger)
        if not health_ok:
            logger.error("❌ Health check failed")
            return False

        logger.info("✅ Health check successful")

        # Test 3: Collection operations
        collection_ok = await test_collection_operations(store, logger)
        if not collection_ok:
            logger.error("❌ Collection operations failed")
            return False

        logger.info("✅ Collection operations successful")

        # Test 4: Vector operations
        vector_ok = await test_vector_operations(store, logger)
        if not vector_ok:
            logger.error("❌ Vector operations failed")
            return False

        logger.info("✅ Vector operations successful")

        # Cleanup
        await cleanup_test_data(store, logger)

        logger.info("=" * 80)
        logger.info("🎉 ALL TESTS PASSED - Qdrant connection is working correctly!")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error("❌ Test suite failed with unexpected error: %s", e)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
