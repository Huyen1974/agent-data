"""
Mock QdrantStore for testing without network calls.
Provides dummy responses for vector operations.
CLI119D4 - Optimized for memory usage with 50+ documents.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MockQdrantStore:
    """Mock implementation of QdrantStore for testing."""

    def __init__(self, collection_name: str = "test_collection", **kwargs):
        self.collection_name = collection_name
        # Optimized storage - only store ID and minimal metadata
        self.storage = {}  # Simple in-memory storage
        self.vector_count = 0
        logger.info(f"MockQdrantStore initialized for collection: {collection_name}")

    def upsert_vector(self, id: str, vector: List[float], payload: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mock upsert_vector operation - optimized for memory."""
        # Only store id and vector length, skip full vector to save memory
        self.storage[id] = {"vector_size": len(vector) if vector else 0, "payload": payload or {}}
        self.vector_count += 1
        # Minimal logging for performance
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Mock upserted vector with id: {id}")
        return {"success": True, "id": id}

    def query_vectors_by_tag(self, tag: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Mock query_vectors_by_tag operation."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Mock querying vectors by tag: {tag}, limit: {limit}")
        # Return empty list for mock
        return []

    def delete_vector(self, id: str) -> Dict[str, Any]:
        """Mock delete_vector operation."""
        if id in self.storage:
            del self.storage[id]
            self.vector_count = max(0, self.vector_count - 1)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Mock deleted vector with id: {id}")
            return {"success": True, "id": id}
        else:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f"Mock vector not found for deletion: {id}")
            return {"success": False, "error": "Vector not found"}

    def collection_exists(self) -> bool:
        """Mock collection_exists check."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Mock collection exists check for: {self.collection_name}")
        return True

    def create_collection(self, vector_size: int = 1536) -> Dict[str, Any]:
        """Mock create_collection operation."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Mock created collection: {self.collection_name} with vector_size: {vector_size}")
        return {"success": True, "collection": self.collection_name}

    def get_collection_info(self) -> Dict[str, Any]:
        """Mock get_collection_info operation."""
        return {"collection": self.collection_name, "vectors_count": self.vector_count, "status": "green"}

    def close(self):
        """Mock close operation."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Mock closed connection for collection: {self.collection_name}")

    def __len__(self):
        """Return number of stored vectors."""
        return self.vector_count
