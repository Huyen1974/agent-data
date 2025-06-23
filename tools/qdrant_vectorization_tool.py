"""Qdrant vectorization tool with Firestore sync for Agent Data system."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

    # Fallback decorator that does nothing
    def retry(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def stop_after_attempt(*args):
        return None

    def wait_exponential(*args, **kwargs):
        return None

    def retry_if_exception_type(*args):
        return None


from ADK.agent_data.config.settings import settings
from ADK.agent_data.vector_store.qdrant_store import QdrantStore
from ADK.agent_data.vector_store.firestore_metadata_manager import FirestoreMetadataManager
from ADK.agent_data.tools.external_tool_registry import get_openai_embedding, openai_async_client, OPENAI_AVAILABLE
from ADK.agent_data.tools.auto_tagging_tool import get_auto_tagging_tool

logger = logging.getLogger(__name__)


class QdrantVectorizationTool:
    """Tool for vectorizing documents and syncing status with Firestore."""

    def __init__(self):
        """Initialize the vectorization tool."""
        self.qdrant_store = None
        self.firestore_manager = None
        self._initialized = False
        self._rate_limiter = {"last_call": 0, "min_interval": 0.3}  # 300ms between calls for free tier

    async def _ensure_initialized(self):
        """Ensure QdrantStore and FirestoreMetadataManager are initialized."""
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

    @(
        retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        )
        if TENACITY_AVAILABLE
        else lambda f: f
    )
    async def _qdrant_operation_with_retry(self, operation_func, *args, **kwargs):
        """Execute Qdrant operations with retry logic for rate limits and connection issues."""
        try:
            await self._rate_limit()
            return await operation_func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "too many requests" in error_msg:
                logger.warning(f"Qdrant rate limit hit, retrying with exponential backoff: {e}")
                # Increase rate limit interval temporarily
                self._rate_limiter["min_interval"] = min(self._rate_limiter["min_interval"] * 1.5, 2.0)
                await asyncio.sleep(self._rate_limiter["min_interval"])
                raise ConnectionError(f"Qdrant rate limit: {e}")
            elif "connection" in error_msg or "timeout" in error_msg:
                logger.warning(f"Qdrant connection issue, retrying: {e}")
                raise ConnectionError(f"Qdrant connection error: {e}")
            else:
                # Don't retry for other errors
                raise

    async def _batch_get_firestore_metadata(self, doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Batch retrieve metadata from Firestore with concurrent processing and RU optimization.
        CLI 140e + CLI 140e.1 optimization for reduced latency and RU costs.
        """
        if not doc_ids:
            return {}

        try:
            # CLI140e.1 RU Optimization: Try batch existence check first
            if hasattr(self.firestore_manager, '_batch_check_documents_exist'):
                existence_map = await self.firestore_manager._batch_check_documents_exist(doc_ids)
                existing_doc_ids = [doc_id for doc_id, exists in existence_map.items() if exists]
                logger.info(f"Batch existence check: {len(existing_doc_ids)}/{len(doc_ids)} documents exist")
            else:
                existing_doc_ids = doc_ids  # Fallback to all doc_ids
                
        except Exception as e:
            logger.warning(f"Batch existence check failed, falling back to individual queries: {e}")
            existing_doc_ids = doc_ids

        # Use semaphore to control concurrency (8 concurrent queries for CLI140e optimization)
        semaphore = asyncio.Semaphore(8)

        async def get_single_metadata(doc_id: str) -> tuple[str, Optional[Dict[str, Any]]]:
            async with semaphore:
                try:
                    # CLI140e.1 RU Optimization: Use optimized metadata retrieval
                    if hasattr(self.firestore_manager, 'get_metadata_with_version'):
                        metadata = await self.firestore_manager.get_metadata_with_version(doc_id)
                    else:
                        # Fallback to standard method
                        metadata = await self.firestore_manager.get_metadata(doc_id)
                    return doc_id, metadata
                except Exception as e:
                    logger.warning(f"Failed to get metadata for {doc_id}: {e}")
                    return doc_id, None

        # Execute all metadata retrievals concurrently (only for existing documents)
        tasks = [get_single_metadata(doc_id) for doc_id in existing_doc_ids]
        
        # CLI140e Optimization: Use timeout for batch operations
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=0.3  # 300ms timeout for batch Firestore operations
            )
        except asyncio.TimeoutError as timeout_error:
            logger.warning(f"Batch Firestore query timed out for {len(existing_doc_ids)} documents")
            # Fallback to individual queries with reduced concurrency
            logger.warning(f"Batch Firestore query failed, falling back to individual queries: {timeout_error}")
            semaphore = asyncio.Semaphore(3)  # Reduced concurrency for fallback
            results = await asyncio.gather(*tasks[:10], return_exceptions=True)  # Limit to 10 for fallback

        # Process results
        metadata_dict = {}
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Metadata retrieval failed: {result}")
                continue

            doc_id, metadata = result
            if metadata:
                metadata_dict[doc_id] = metadata

        logger.debug(f"Retrieved metadata for {len(metadata_dict)}/{len(doc_ids)} documents")
        return metadata_dict

    def _filter_by_metadata(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filter results by metadata criteria."""
        if not filters:
            return results

        filtered = []
        for result in results:
            match = True
            for key, value in filters.items():
                if key not in result or result[key] != value:
                    match = False
                    break
            if match:
                filtered.append(result)

        return filtered

    def _filter_by_tags(self, results: List[Dict[str, Any]], tags: List[str]) -> List[Dict[str, Any]]:
        """Filter results by auto-tags."""
        if not tags:
            return results

        filtered = []
        for result in results:
            result_tags = result.get("auto_tags", [])
            if any(tag in result_tags for tag in tags):
                filtered.append(result)

        return filtered

    def _filter_by_path(self, results: List[Dict[str, Any]], path_query: str) -> List[Dict[str, Any]]:
        """Filter results by hierarchy path."""
        if not path_query:
            return results

        filtered = []
        for result in results:
            hierarchy_path = self._build_hierarchy_path(result)
            if path_query.lower() in hierarchy_path.lower():
                filtered.append(result)

        return filtered

    def _build_hierarchy_path(self, result: Dict[str, Any]) -> str:
        """Build hierarchy path from metadata."""
        level_1 = result.get("level_1_category", "")
        level_2 = result.get("level_2_category", "")

        if level_1 and level_2:
            return f"{level_1} > {level_2}"
        elif level_1:
            return level_1
        else:
            return "Uncategorized"

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
        Perform hybrid RAG search combining Qdrant semantic search with Firestore metadata filtering.
        CLI 140e implementation with batch processing optimization.
        """
        await self._ensure_initialized()

        try:
            # Step 1: Qdrant semantic search with retry logic
            qdrant_results = await self._qdrant_operation_with_retry(
                self.qdrant_store.semantic_search,
                query_text=query_text,
                limit=limit * 2,  # Get more results for filtering
                tag=qdrant_tag,
                score_threshold=score_threshold,
            )

            if not qdrant_results.get("results"):
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
                        "score_threshold": score_threshold,
                    },
                }

            # Extract doc_ids and scores from Qdrant results
            qdrant_doc_ids = []
            qdrant_scores = {}
            for result in qdrant_results["results"]:
                doc_id = result["metadata"].get("doc_id")
                if doc_id:
                    qdrant_doc_ids.append(doc_id)
                    qdrant_scores[doc_id] = result["score"]

            # Step 2: Batch retrieve Firestore metadata
            batch_metadata = await self._batch_get_firestore_metadata(qdrant_doc_ids)

            # Combine Qdrant and Firestore data
            firestore_results = []
            for doc_id in qdrant_doc_ids:
                if doc_id in batch_metadata:
                    metadata = batch_metadata[doc_id]
                    metadata["_doc_id"] = doc_id
                    metadata["_qdrant_score"] = qdrant_scores[doc_id]
                    firestore_results.append(metadata)

            # Step 3: Apply filters
            filtered_results = firestore_results
            if metadata_filters:
                filtered_results = self._filter_by_metadata(filtered_results, metadata_filters)
            if tags:
                filtered_results = self._filter_by_tags(filtered_results, tags)
            if path_query:
                filtered_results = self._filter_by_path(filtered_results, path_query)

            # Step 4: Sort by Qdrant score and limit
            filtered_results.sort(key=lambda x: x.get("_qdrant_score", 0), reverse=True)
            final_results = filtered_results[:limit]

            # Step 5: Enrich results with hierarchy and formatting
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
            logger.error(f"RAG search failed for query '{query_text}': {e}")
            return {
                "status": "failed",
                "query": query_text,
                "results": [],
                "count": 0,
                "error": str(e),
            }

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
        CLI140f Performance Optimization: Target <0.3s per call.

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
        start_time = time.time()
        await self._ensure_initialized()

        if not OPENAI_AVAILABLE or not openai_async_client:
            return {
                "status": "failed",
                "error": "OpenAI async client not available for embedding generation",
                "doc_id": doc_id,
                "latency": time.time() - start_time,
                "performance_target_met": False
            }

        try:
            # CLI140f: Parallel execution of tasks to reduce latency
            tasks = []
            
            # Task 1: Set vectorStatus to pending in Firestore if enabled
            if update_firestore:
                tasks.append(self._update_vector_status(doc_id, "pending", metadata))

            # Task 2: Generate embedding (main bottleneck)
            embedding_task = get_openai_embedding(agent_context=None, text_to_embed=content)
            tasks.append(embedding_task)

            # CLI140f: Execute initial tasks concurrently with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=0.2  # 200ms timeout for initial operations
                )
                
                # Extract embedding result
                embedding_result = results[-1]  # Last task is always embedding
                if isinstance(embedding_result, Exception):
                    raise embedding_result
                    
            except asyncio.TimeoutError:
                error_msg = "Embedding generation timeout"
                if update_firestore:
                    await self._update_vector_status(doc_id, "failed", metadata, error_msg)
                return {
                    "status": "timeout", 
                    "error": error_msg, 
                    "doc_id": doc_id,
                    "latency": time.time() - start_time,
                    "performance_target_met": False
                }

            if not embedding_result or "embedding" not in embedding_result:
                error_msg = "Failed to generate embedding"
                if update_firestore:
                    await self._update_vector_status(doc_id, "failed", metadata, error_msg)
                return {
                    "status": "failed", 
                    "error": error_msg, 
                    "doc_id": doc_id,
                    "latency": time.time() - start_time,
                    "performance_target_met": False
                }

            embedding = embedding_result["embedding"]

            # CLI140f: Prepare metadata efficiently
            qdrant_metadata = metadata.copy() if metadata else {}
            qdrant_metadata.update(
                {
                    "doc_id": doc_id,
                    "content_preview": content[:200] + "..." if len(content) > 200 else content,
                    "vectorized_at": datetime.utcnow().isoformat(),
                    "embedding_model": "text-embedding-ada-002",
                    "content_length": len(content),
                }
            )

            # CLI140f: Parallel execution of auto-tagging and vector upsert
            final_tasks = []
            
            # Task 1: Generate auto-tags if enabled (optional, non-blocking)
            if enable_auto_tagging:
                try:
                    auto_tagging_tool = get_auto_tagging_tool()
                    auto_tag_task = auto_tagging_tool.enhance_metadata_with_tags(
                        doc_id, content, qdrant_metadata, max_tags=5
                    )
                    final_tasks.append(auto_tag_task)
                except Exception as e:
                    logger.warning(f"Failed to initialize auto-tagging for doc_id {doc_id}: {e}")
                    final_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task

            # Task 2: Upsert vector to Qdrant (critical path)
            vector_task = self._qdrant_operation_with_retry(
                self.qdrant_store.upsert_vector,
                vector_id=doc_id, 
                vector=embedding, 
                metadata=qdrant_metadata, 
                tag=tag
            )
            final_tasks.append(vector_task)

            # CLI140f: Execute final tasks with timeout
            try:
                final_results = await asyncio.wait_for(
                    asyncio.gather(*final_tasks, return_exceptions=True),
                    timeout=0.15  # 150ms timeout for final operations
                )
                
                # Process results
                if enable_auto_tagging and len(final_results) > 1:
                    auto_tag_result = final_results[0]
                    if not isinstance(auto_tag_result, Exception):
                        qdrant_metadata = auto_tag_result
                        logger.debug(f"Enhanced metadata with auto-tags for doc_id: {doc_id}")
                
                vector_result = final_results[-1]  # Last task is always vector upsert
                if isinstance(vector_result, Exception):
                    raise vector_result
                    
            except asyncio.TimeoutError:
                # CLI140f: Continue with basic metadata if auto-tagging times out
                logger.warning(f"Auto-tagging timeout for doc_id {doc_id}, proceeding with basic metadata")
                vector_result = await self._qdrant_operation_with_retry(
                    self.qdrant_store.upsert_vector,
                    vector_id=doc_id, 
                    vector=embedding, 
                    metadata=qdrant_metadata, 
                    tag=tag
                )

            if not vector_result.get("success"):
                error_msg = f"Failed to upsert vector: {vector_result.get('error', 'Unknown error')}"
                if update_firestore:
                    await self._update_vector_status(doc_id, "failed", metadata, error_msg)
                return {
                    "status": "failed", 
                    "error": error_msg, 
                    "doc_id": doc_id,
                    "latency": time.time() - start_time,
                    "performance_target_met": False
                }

            # CLI140f: Update vectorStatus to completed in Firestore (non-blocking)
            if update_firestore:
                # Fire and forget for performance
                asyncio.create_task(self._update_vector_status(doc_id, "completed", metadata))

            latency = time.time() - start_time
            performance_target_met = latency < 0.3

            return {
                "status": "success",
                "doc_id": doc_id,
                "vector_id": vector_result.get("vector_id"),
                "embedding_dimension": len(embedding),
                "metadata_keys": list(qdrant_metadata.keys()),
                "firestore_updated": update_firestore,
                "latency": latency,
                "performance_target_met": performance_target_met
            }

        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Failed to vectorize document {doc_id}: {e}")
            if update_firestore:
                # Fire and forget for performance
                asyncio.create_task(self._update_vector_status(doc_id, "failed", metadata, str(e)))
            return {
                "status": "failed", 
                "error": str(e), 
                "doc_id": doc_id,
                "latency": latency,
                "performance_target_met": False
            }

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
        Vectorize multiple documents in batch with CLI140f performance optimization.
        Target: <5s for 100 documents, <0.3s per document.

        Args:
            documents: List of document dictionaries with 'doc_id' and 'content' keys
            tag: Optional tag for all documents
            update_firestore: Whether to update Firestore with vectorStatus

        Returns:
            Batch operation results
        """
        start_time = time.time()
        await self._ensure_initialized()

        if not documents:
            return {"status": "failed", "error": "No documents provided", "results": []}

        # CLI140f: Optimized batch processing with concurrent execution
        batch_size = min(10, len(documents))  # Process in batches of 10 for optimal performance
        results = []
        successful = 0
        failed = 0

        # CLI140f: Process documents in concurrent batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_start = time.time()
            
            # Create tasks for concurrent processing
            tasks = []
            for doc in batch:
                doc_id = doc.get("doc_id")
                content = doc.get("content")
                metadata = doc.get("metadata", {})

                if not doc_id or not content:
                    result = {"status": "failed", "error": "Missing doc_id or content", "doc_id": doc_id or "unknown"}
                    results.append(result)
                    failed += 1
                    continue

                # CLI140f: Create vectorization task with timeout
                task = asyncio.create_task(
                    self._vectorize_document_with_timeout(
                        doc_id=doc_id, 
                        content=content, 
                        metadata=metadata, 
                        tag=tag, 
                        update_firestore=update_firestore,
                        timeout=0.5  # 500ms timeout per document
                    )
                )
                tasks.append(task)

            # CLI140f: Execute batch with overall timeout
            try:
                batch_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=2.0  # 2s timeout per batch
                )
                
                # Process batch results
                for result in batch_results:
                    if isinstance(result, Exception):
                        results.append({
                            "status": "failed",
                            "error": str(result),
                            "doc_id": "unknown"
                        })
                        failed += 1
                    else:
                        results.append(result)
                        if result["status"] == "success":
                            successful += 1
                        else:
                            failed += 1
                            
            except asyncio.TimeoutError:
                logger.warning(f"Batch timeout for documents {i}-{i+batch_size}")
                for j in range(len(tasks)):
                    results.append({
                        "status": "timeout",
                        "doc_id": batch[j].get("doc_id", "unknown"),
                        "error": "Batch timeout"
                    })
                    failed += 1
            
            batch_latency = time.time() - batch_start
            logger.debug(f"Processed vectorization batch {i//batch_size + 1} in {batch_latency:.3f}s")

        total_latency = time.time() - start_time
        performance_target_met = total_latency < 5.0 and len(documents) <= 100

        return {
            "status": "completed",
            "total_documents": len(documents),
            "successful": successful,
            "failed": failed,
            "total_latency": total_latency,
            "avg_latency_per_doc": total_latency / len(documents) if documents else 0,
            "performance_target_met": performance_target_met,
            "results": results,
        }

    async def _vectorize_document_with_timeout(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tag: Optional[str] = None,
        update_firestore: bool = True,
        timeout: float = 0.5
    ) -> Dict[str, Any]:
        """
        Vectorize document with timeout for CLI140f performance optimization.
        """
        try:
            return await asyncio.wait_for(
                self.vectorize_document(
                    doc_id=doc_id,
                    content=content,
                    metadata=metadata,
                    tag=tag,
                    update_firestore=update_firestore,
                    enable_auto_tagging=False  # CLI140f: Disable auto-tagging for batch performance
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Vectorization timeout for document {doc_id}")
            return {
                "status": "timeout",
                "doc_id": doc_id,
                "error": f"Vectorization timeout after {timeout}s"
            }


# Global instance for tool functions
_vectorization_tool = None


def get_vectorization_tool() -> QdrantVectorizationTool:
    """Get or create the global vectorization tool instance."""
    global _vectorization_tool
    if _vectorization_tool is None:
        _vectorization_tool = QdrantVectorizationTool()
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
    Batch vectorize multiple documents using the global vectorization tool.

    Args:
        documents: List of document dictionaries with 'doc_id' and 'content' keys
        tag: Optional tag for grouping
        update_firestore: Whether to update Firestore with vectorStatus

    Returns:
        Result dictionary with batch operation status
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
    Perform hybrid RAG search using the global vectorization tool.
    CLI 140e implementation with batch processing optimization.

    Args:
        query_text: Text to search for semantically similar documents
        metadata_filters: Optional metadata filters to apply
        tags: Optional list of tags to filter by
        path_query: Optional hierarchy path query
        limit: Maximum number of results to return
        score_threshold: Minimum similarity score threshold
        qdrant_tag: Optional Qdrant tag filter

    Returns:
        Result dictionary with search results and metadata
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
