"""Base VectorStore interface for Agent Data vector operations."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class VectorStore(ABC):
    """Abstract base class for vector storage implementations."""

    @abstractmethod
    async def upsert_vector(
        self,
        vector_id: str,
        vector: list[float] | np.ndarray,
        metadata: dict[str, Any] | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        """
        Upsert (insert or update) a vector with metadata.

        Args:
            vector_id: Unique identifier for the vector
            vector: The vector data as list or numpy array
            metadata: Optional metadata dictionary
            tag: Optional tag for grouping vectors

        Returns:
            Result dictionary with operation status
        """
        pass

    @abstractmethod
    async def query_vectors_by_tag(
        self,
        tag: str,
        query_vector: list[float] | np.ndarray | None = None,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Query vectors by tag with optional similarity search.

        Args:
            tag: Tag to filter vectors
            query_vector: Optional vector for similarity search
            limit: Maximum number of results
            threshold: Minimum similarity threshold

        Returns:
            List of matching vectors with metadata and scores
        """
        pass

    @abstractmethod
    async def delete_vectors_by_tag(self, tag: str) -> dict[str, Any]:
        """
        Delete all vectors with a specific tag.

        Args:
            tag: Tag identifying vectors to delete

        Returns:
            Result dictionary with deletion status
        """
        pass

    @abstractmethod
    async def get_vector_count(self) -> int:
        """
        Get total number of vectors stored.

        Returns:
            Total vector count
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector store is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass
