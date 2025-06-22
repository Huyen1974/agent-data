"""Qdrant vectorization tool with Firestore sync for Agent Data system."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

from ..config.settings import settings
from ..vector_store.qdrant_store import QdrantStore
from ..vector_store.firestore_metadata_manager import FirestoreMetadataManager
from ..embedding.embedding_provider import EmbeddingProvider, EmbeddingError
from ..embedding.openai_embedding_provider import get_default_embedding_provider
from .auto_tagging_tool import get_auto_tagging_tool
from ..event.event_manager import get_event_manager

logger = logging.getLogger(__name__)


class QdrantVectorizationTool:
    """Tool for vectorizing documents and syncing status with Firestore."""

    def __init__(self, embedding_provider: Optional[EmbeddingProvider] = None):
        """Initialize the vectorization tool.

        Args:
            embedding_provider: Optional embedding provider. Defaults to OpenAI provider.
        """
        self.qdrant_store = None
        self.firestore_manager = None
        self.embedding_provider = embedding_provider
        self._initialized = False
        self._rate_limiter = {"last_call": 0, "min_interval": 0.3}  # 300ms between calls for free tier

    async def _ensure_initialized(self):
        """Ensure QdrantStore, FirestoreMetadataManager, and EmbeddingProvider are initialized."""
        if self._initialized:
            return

        try:
            # Initialize QdrantStore
            config = settings.get_qdrant_config()
            self.qdrant_store = QdrantStore(
                url=config["url"],
                api_key=config["api_key"],
                collection_name=config["collection_name"],
                vector_size=config["vector_size"],
            )

            # Initialize FirestoreMetadataManager
            firestore_config = settings.get_firestore_config()
            self.firestore_manager = FirestoreMetadataManager(
                project_id=firestore_config.get("project_id"),
                collection_name=firestore_config.get("metadata_collection", "document_metadata"),
            )

            # Initialize EmbeddingProvider if not provided
            if self.embedding_provider is None:
                self.embedding_provider = get_default_embedding_provider()

            self._initialized = True
            logger.info("QdrantVectorizationTool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize QdrantVectorizationTool: {e}")
            raise

    async def _rate_limit(self):
        """Ensure rate limiting for free tier constraints."""
        current_time = time.time()
        time_since_last = current_time - self._rate_limiter["last_call"]

        if time_since_last < self._rate_limiter["min_interval"]:
            sleep_time = self._rate_limiter["min_interval"] - time_since_last
            await asyncio.sleep(sleep_time)

        self._rate_limiter["last_call"] = time.time()

    async def vectorize_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = None,
        update_firestore: bool = True,
        enable_auto_tagging: bool = True,
    ) -> Dict[str, Any]:
        """
        Vectorize a document and store in Qdrant with optional Firestore sync and auto-tagging.

        Args:
            doc_id: Unique document identifier
            content: Document content to vectorize
            metadata: Optional metadata dictionary
            tag: Optional tag for grouping
            update_firestore: Whether to update Firestore with vectorStatus
            enable_auto_tagging: Whether to generate auto-tags using OpenAI

        Returns:
            Result dictionary with operation status
        """
        await self._ensure_initialized()

        try:
            # Set vectorStatus to pending in Firestore if enabled
            if update_firestore:
                await self._update_vector_status(doc_id, "pending", metadata)

            # Generate embedding using the provider interface
            embedding = await self.embedding_provider.embed_single(content)

            # Prepare metadata for Qdrant
            qdrant_metadata = metadata.copy() if metadata else {}
            qdrant_metadata.update(
                {
                    "doc_id": doc_id,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "vectorized_at": datetime.utcnow().isoformat(),
                    "embedding_model": self.embedding_provider.get_model_name(),
                    "content_length": len(content),
                }
            )

            # Generate auto-tags if enabled
            if enable_auto_tagging:
                try:
                    auto_tagging_tool = get_auto_tagging_tool()
                    enhanced_metadata = await auto_tagging_tool.enhance_metadata_with_tags(
                        doc_id, content, qdrant_metadata, max_tags=5
                    )
                    qdrant_metadata = enhanced_metadata
                    logger.debug(f"Enhanced metadata with auto-tags for doc_id: {doc_id}")
                except Exception as e:
                    logger.warning(f"Failed to generate auto-tags for doc_id {doc_id}: {e}")
                    # Continue without auto-tags

            # Upsert vector to Qdrant
            vector_result = await self.qdrant_store.upsert_vector(
                vector_id=doc_id, vector=embedding, metadata=qdrant_metadata, tag=tag
            )

            if not vector_result.get("success"):
                error_msg = f"Failed to upsert vector: {vector_result.get('error', 'Unknown error')}"
                if update_firestore:
                    await self._update_vector_status(doc_id, "failed", metadata, error_msg)
                return {"status": "failed", "error": error_msg, "doc_id": doc_id}

            # Update vectorStatus to completed in Firestore
            if update_firestore:
                await self._update_vector_status(doc_id, "completed", metadata)

            # Publish save_document event via Pub/Sub A2A communication
            try:
                event_manager = get_event_manager()
                event_result = await event_manager.publish_save_document_event(
                    doc_id=doc_id,
                    metadata={
                        "vector_id": vector_result.get("vector_id"),
                        "embedding_dimension": len(embedding),
                        "firestore_updated": update_firestore,
                        "auto_tagged": enable_auto_tagging,
                    },
                )
                logger.debug(f"Event publishing result for {doc_id}: {event_result}")
            except Exception as e:
                logger.warning(f"Failed to publish save_document event for {doc_id}: {e}")
                # Don't fail the vectorization if event publishing fails

            return {
                "status": "success",
                "doc_id": doc_id,
                "vector_id": vector_result.get("vector_id"),
                "embedding_dimension": len(embedding),
                "metadata_keys": list(qdrant_metadata.keys()),
                "firestore_updated": update_firestore,
            }

        except EmbeddingError as e:
            logger.error(f"Embedding generation failed for document {doc_id}: {e}")
            if update_firestore:
                await self._update_vector_status(doc_id, "failed", metadata, str(e))
            return {"status": "failed", "error": str(e), "doc_id": doc_id}
        except Exception as e:
            logger.error(f"Failed to vectorize document {doc_id}: {e}")
            if update_firestore:
                await self._update_vector_status(doc_id, "failed", metadata, str(e))
            return {"status": "failed", "error": str(e), "doc_id": doc_id}

    async def _update_vector_status(
        self, doc_id: str, status: str, metadata: Optional[Dict[str, Any]] = None, error_message: Optional[str] = None
    ):
        """
        Update vectorStatus in Firestore.

        Args:
            doc_id: Document identifier
            status: Vector status (pending, completed, failed)
            metadata: Optional metadata to include
            error_message: Optional error message for failed status
        """
        try:
            firestore_metadata = {
                "vectorStatus": status,
                "lastUpdated": datetime.utcnow().isoformat(),
                "doc_id": doc_id,
            }

            if metadata:
                firestore_metadata.update(metadata)

            if error_message and status == "failed":
                firestore_metadata["error"] = error_message

            await self.firestore_manager.save_metadata(doc_id, firestore_metadata)
            logger.debug(f"Updated vectorStatus to '{status}' for doc_id: {doc_id}")

        except Exception as e:
            logger.error(f"Failed to update vectorStatus in Firestore for {doc_id}: {e}")
            # Don't raise here to avoid breaking the main vectorization flow

    async def batch_vectorize_documents(
        self, documents: List[Dict[str, Any]], tag: Optional[str] = None, update_firestore: bool = True
    ) -> Dict[str, Any]:
        """
        Vectorize multiple documents in batch with rate-limit protection.

        Args:
            documents: List of document dictionaries with 'doc_id' and 'content' keys
            tag: Optional tag for all documents
            update_firestore: Whether to update Firestore with vectorStatus

        Returns:
            Batch operation results
        """
        await self._ensure_initialized()

        # Get batch configuration from settings
        config = settings.get_qdrant_config()
        batch_size = config.get("batch_size", 100)
        sleep_between_batches = config.get("sleep_between_batches", 0.35)

        results = []
        successful = 0
        failed = 0
        batch_count = 0

        # Process documents in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            batch_count += 1

            logger.info(
                f"Processing batch {batch_count}/{(len(documents) + batch_size - 1) // batch_size} "
                f"({len(batch)} documents)"
            )

            # Process each document in the batch
            for doc in batch:
                doc_id = doc.get("doc_id")
                content = doc.get("content")
                metadata = doc.get("metadata", {})

                if not doc_id or not content:
                    result = {"status": "failed", "error": "Missing doc_id or content", "doc_id": doc_id or "unknown"}
                    results.append(result)
                    failed += 1
                    continue

                # Apply rate limiting per document
                await self._rate_limit()

                result = await self.vectorize_document(
                    doc_id=doc_id, content=content, metadata=metadata, tag=tag, update_firestore=update_firestore
                )

                results.append(result)
                if result["status"] == "success":
                    successful += 1
                else:
                    failed += 1

            # Sleep between batches to prevent rate limits (except for the last batch)
            if i + batch_size < len(documents):
                logger.debug(f"Sleeping {sleep_between_batches}s between batches to prevent rate limits")
                await asyncio.sleep(sleep_between_batches)

        return {
            "status": "completed",
            "total_documents": len(documents),
            "successful": successful,
            "failed": failed,
            "batches_processed": batch_count,
            "batch_size": batch_size,
            "sleep_between_batches": sleep_between_batches,
            "results": results,
        }

    async def rag_search(
        self,
        query_text: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        path_query: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.5,
        qdrant_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform RAG (Retrieval-Augmented Generation) search combining Qdrant semantic search
        with Firestore metadata filtering.

        Args:
            query_text: Text to search for semantically similar content
            metadata_filters: Optional metadata filters (e.g., {"author": "John Doe", "year": 2024})
            tags: Optional list of tags to filter by
            path_query: Optional path segment to search in hierarchy
            limit: Maximum number of results
            score_threshold: Minimum similarity threshold for Qdrant search
            qdrant_tag: Optional Qdrant tag filter for vector search

        Returns:
            Dictionary with enriched search results combining vector similarity and metadata
        """
        await self._ensure_initialized()

        try:
            # Step 1: Perform semantic search in Qdrant
            qdrant_results = await self.qdrant_store.semantic_search(
                query_text=query_text,
                limit=limit * 2,  # Get more results to account for filtering
                tag=qdrant_tag,
                score_threshold=score_threshold,
            )

            if qdrant_results["status"] != "success":
                return {
                    "status": "failed",
                    "error": f"Qdrant search failed: {qdrant_results.get('error', 'Unknown error')}",
                    "query": query_text,
                    "results": [],
                }

            # Extract doc_ids from Qdrant results
            qdrant_doc_ids = []
            qdrant_scores = {}
            for result in qdrant_results["results"]:
                doc_id = result["metadata"].get("doc_id")
                if doc_id:
                    qdrant_doc_ids.append(doc_id)
                    qdrant_scores[doc_id] = result["score"]

            if not qdrant_doc_ids:
                return {
                    "status": "success",
                    "query": query_text,
                    "results": [],
                    "count": 0,
                    "rag_info": {
                        "qdrant_results": 0,
                        "firestore_filtered": 0,
                        "metadata_filters": metadata_filters,
                        "tags": tags,
                        "path_query": path_query,
                    },
                }

            # Step 2: Get Firestore metadata for Qdrant results (optimized batch query)
            firestore_results = []
            try:
                # Batch query optimization for better performance
                batch_metadata = await self._batch_get_firestore_metadata(qdrant_doc_ids)
                for doc_id in qdrant_doc_ids:
                    if doc_id in batch_metadata:
                        metadata = batch_metadata[doc_id]
                        metadata["_doc_id"] = doc_id
                        metadata["_qdrant_score"] = qdrant_scores[doc_id]
                        firestore_results.append(metadata)
            except Exception as e:
                logger.warning(f"Batch Firestore query failed, falling back to individual queries: {e}")
                # Fallback to individual queries
                for doc_id in qdrant_doc_ids:
                    try:
                        metadata = await self.firestore_manager.get_metadata_with_version(doc_id)
                        if metadata:
                            metadata["_doc_id"] = doc_id
                            metadata["_qdrant_score"] = qdrant_scores[doc_id]
                            firestore_results.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to get metadata for doc_id {doc_id}: {e}")

            # Step 3: Apply Firestore-based filters
            filtered_results = firestore_results

            # Filter by metadata
            if metadata_filters:
                filtered_results = self._filter_by_metadata(filtered_results, metadata_filters)

            # Filter by tags
            if tags:
                filtered_results = self._filter_by_tags(filtered_results, tags)

            # Filter by path
            if path_query:
                filtered_results = self._filter_by_path(filtered_results, path_query)

            # Step 4: Sort by Qdrant score and limit results
            filtered_results.sort(key=lambda x: x.get("_qdrant_score", 0), reverse=True)
            final_results = filtered_results[:limit]

            # Step 5: Enrich results with RAG information
            enriched_results = []
            for result in final_results:
                enriched_result = {
                    "doc_id": result["_doc_id"],
                    "qdrant_score": result["_qdrant_score"],
                    "metadata": {k: v for k, v in result.items() if not k.startswith("_")},
                    "content_preview": result.get("content_preview", ""),
                    "auto_tags": result.get("auto_tags", []),
                    "hierarchy_path": self._build_hierarchy_path(result),
                    "last_updated": result.get("lastUpdated"),
                    "version": result.get("version", 1),
                }
                enriched_results.append(enriched_result)

            return {
                "status": "success",
                "query": query_text,
                "results": enriched_results,
                "count": len(enriched_results),
                "rag_info": {
                    "qdrant_results": len(qdrant_results["results"]),
                    "firestore_filtered": len(filtered_results),
                    "metadata_filters": metadata_filters,
                    "tags": tags,
                    "path_query": path_query,
                    "score_threshold": score_threshold,
                },
            }

        except Exception as e:
            logger.error(f"Failed to perform RAG search for '{query_text}': {e}")
            return {
                "status": "failed",
                "error": str(e),
                "query": query_text,
                "results": [],
            }

    def _filter_by_metadata(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter results by metadata criteria."""
        filtered = []
        for result in results:
            match = True
            for field, value in filters.items():
                if field in result:
                    if isinstance(value, str) and isinstance(result[field], str):
                        # Case-insensitive string comparison
                        if value.lower() not in result[field].lower():
                            match = False
                            break
                    elif result[field] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            if match:
                filtered.append(result)
        return filtered

    def _filter_by_tags(self, results: List[Dict[str, Any]], tags: List[str]) -> List[Dict[str, Any]]:
        """Filter results by tags."""
        filtered = []
        clean_tags = [tag.lower().strip() for tag in tags]
        for result in results:
            result_tags = result.get("auto_tags", [])
            if any(tag.lower() in clean_tags for tag in result_tags):
                filtered.append(result)
        return filtered

    def _filter_by_path(self, results: List[Dict[str, Any]], path_query: str) -> List[Dict[str, Any]]:
        """Filter results by hierarchical path."""
        filtered = []
        path_query = path_query.lower().strip()
        hierarchy_levels = [
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "level_4_category",
            "level_5_category",
            "level_6_category",
        ]

        for result in results:
            match = False
            for level in hierarchy_levels:
                if level in result and result[level]:
                    if path_query in result[level].lower():
                        match = True
                        break
            if match:
                filtered.append(result)
        return filtered

    def _build_hierarchy_path(self, result: Dict[str, Any]) -> str:
        """Build hierarchical path from metadata."""
        path_parts = []
        hierarchy_levels = [
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "level_4_category",
            "level_5_category",
            "level_6_category",
        ]

        for level in hierarchy_levels:
            if level in result and result[level]:
                path_parts.append(result[level])

        return " > ".join(path_parts) if path_parts else "Uncategorized"

    async def _batch_get_firestore_metadata(self, doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Batch get Firestore metadata for multiple documents (CLI 140e optimization)."""
        if not self.firestore_manager:
            return {}

        try:
            # Use batch get if available, otherwise fall back to individual queries
            if hasattr(self.firestore_manager, "batch_get_metadata"):
                return await self.firestore_manager.batch_get_metadata(doc_ids)
            else:
                # Fallback: concurrent individual queries for better performance
                import asyncio

                async def get_single_metadata(doc_id: str) -> tuple[str, Dict[str, Any]]:
                    try:
                        metadata = await self.firestore_manager.get_metadata_with_version(doc_id)
                        return doc_id, metadata if metadata else {}
                    except Exception as e:
                        logger.warning(f"Failed to get metadata for {doc_id}: {e}")
                        return doc_id, {}

                # Execute concurrent queries with limited concurrency
                semaphore = asyncio.Semaphore(10)  # Limit concurrent Firestore queries

                async def bounded_get_metadata(doc_id: str):
                    async with semaphore:
                        return await get_single_metadata(doc_id)

                tasks = [bounded_get_metadata(doc_id) for doc_id in doc_ids]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results
                batch_metadata = {}
                for result in results:
                    if isinstance(result, tuple) and len(result) == 2:
                        doc_id, metadata = result
                        if metadata:
                            batch_metadata[doc_id] = metadata

                return batch_metadata

        except Exception as e:
            logger.error(f"Batch Firestore metadata query failed: {e}")
            return {}


# Global instance for tool functions
_vectorization_tool = None


def get_vectorization_tool(embedding_provider: Optional[EmbeddingProvider] = None) -> QdrantVectorizationTool:
    """Get or create the global vectorization tool instance.

    Args:
        embedding_provider: Optional embedding provider. If provided and no global instance
                          exists, creates a new instance with this provider.
    """
    global _vectorization_tool
    if _vectorization_tool is None:
        _vectorization_tool = QdrantVectorizationTool(embedding_provider=embedding_provider)
    return _vectorization_tool


# Tool function for external use
async def qdrant_vectorize_document(
    doc_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    tag: Optional[str] = None,
    update_firestore: bool = True,
) -> Dict[str, Any]:
    """
    Vectorize a document and store in Qdrant with Firestore sync.

    Args:
        doc_id: Unique document identifier
        content: Document content to vectorize
        metadata: Optional metadata dictionary
        tag: Optional tag for grouping
        update_firestore: Whether to update Firestore with vectorStatus

    Returns:
        Result dictionary with operation status
    """
    tool = get_vectorization_tool()
    return await tool.vectorize_document(doc_id, content, metadata, tag, update_firestore)


async def qdrant_batch_vectorize_documents(
    documents: List[Dict[str, Any]], tag: Optional[str] = None, update_firestore: bool = True
) -> Dict[str, Any]:
    """
    Vectorize multiple documents in batch with Firestore sync.

    Args:
        documents: List of document dictionaries with 'doc_id' and 'content' keys
        tag: Optional tag for all documents
        update_firestore: Whether to update Firestore with vectorStatus

    Returns:
        Batch operation results
    """
    tool = get_vectorization_tool()
    return await tool.batch_vectorize_documents(documents, tag, update_firestore)


async def qdrant_rag_search(
    query_text: str,
    metadata_filters: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None,
    path_query: Optional[str] = None,
    limit: int = 10,
    score_threshold: float = 0.5,
    qdrant_tag: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Perform RAG (Retrieval-Augmented Generation) search combining Qdrant semantic search
    with Firestore metadata filtering.

    Args:
        query_text: Text to search for semantically similar content
        metadata_filters: Optional metadata filters (e.g., {"author": "John Doe", "year": 2024})
        tags: Optional list of tags to filter by
        path_query: Optional path segment to search in hierarchy
        limit: Maximum number of results
        score_threshold: Minimum similarity threshold for Qdrant search
        qdrant_tag: Optional Qdrant tag filter for vector search

    Returns:
        Dictionary with enriched search results combining vector similarity and metadata
    """
    tool = get_vectorization_tool()
    return await tool.rag_search(
        query_text=query_text,
        metadata_filters=metadata_filters,
        tags=tags,
        path_query=path_query,
        limit=limit,
        score_threshold=score_threshold,
        qdrant_tag=qdrant_tag,
    )
