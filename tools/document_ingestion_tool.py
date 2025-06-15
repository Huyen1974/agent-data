"""
Optimized Document Ingestion Tool for Agent Data system.
CLI140f Performance Optimization: Target <0.3s per call, <5s for 100 docs batch.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor
import hashlib

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
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
from ADK.agent_data.vector_store.firestore_metadata_manager import FirestoreMetadataManager
from ADK.agent_data.tools.external_tool_registry import get_openai_embedding, openai_async_client, OPENAI_AVAILABLE

logger = logging.getLogger(__name__)


class DocumentIngestionTool:
    """
    Optimized document ingestion tool with performance enhancements.
    CLI140f: Target <0.3s per call, <5s for 100 docs batch processing.
    """

    def __init__(self):
        """Initialize the document ingestion tool with performance optimizations."""
        self.firestore_manager = None
        self._initialized = False
        self._batch_size = 10  # CLI140f: Optimized batch size for performance
        self._cache = {}  # Simple in-memory cache for metadata
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._performance_metrics = {
            "total_calls": 0,
            "total_time": 0.0,
            "avg_latency": 0.0,
            "batch_calls": 0,
            "batch_time": 0.0
        }

    async def _ensure_initialized(self):
        """Ensure FirestoreMetadataManager is initialized with timeout."""
        if self._initialized:
            return

        try:
            # CLI140f: Fast initialization with timeout
            firestore_config = settings.get_firestore_config()
            self.firestore_manager = FirestoreMetadataManager(
                project_id=firestore_config.get("project_id"),
                collection_name=firestore_config.get("metadata_collection", "document_metadata"),
            )
            self._initialized = True
            logger.info("DocumentIngestionTool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize DocumentIngestionTool: {e}")
            raise

    def _get_cache_key(self, doc_id: str, content_hash: str) -> str:
        """Generate cache key for document."""
        return f"{doc_id}:{content_hash}"

    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - timestamp) < self._cache_ttl

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content to detect changes."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:8]

    @(
        retry(
            stop=stop_after_attempt(2),  # CLI140f: Reduced retries for speed
            wait=wait_exponential(multiplier=0.5, min=0.1, max=1),  # CLI140f: Faster retry
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        )
        if TENACITY_AVAILABLE
        else lambda f: f
    )
    async def _save_document_metadata(
        self, 
        doc_id: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save document metadata with performance optimizations.
        CLI140f: Target <0.1s for metadata operations.
        """
        start_time = time.time()
        
        try:
            # CLI140f: Generate content hash for caching
            content_hash = self._get_content_hash(content)
            cache_key = self._get_cache_key(doc_id, content_hash)
            
            # CLI140f: Check cache first
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if self._is_cache_valid(timestamp):
                    logger.debug(f"Cache hit for document {doc_id}")
                    return cached_data

            # CLI140f: Prepare optimized metadata
            document_metadata = {
                "doc_id": doc_id,
                "content_preview": content[:200] if len(content) > 200 else content,
                "content_length": len(content),
                "content_hash": content_hash,
                "ingestion_timestamp": datetime.utcnow().isoformat(),
                "version": 1,
                "status": "ingested"
            }
            
            # CLI140f: Merge with provided metadata
            if metadata:
                document_metadata.update(metadata)

            # CLI140f: Fast Firestore save with timeout
            await asyncio.wait_for(
                self.firestore_manager.save_metadata(doc_id, document_metadata),
                timeout=0.2  # 200ms timeout for Firestore operations
            )

            # CLI140f: Cache the result
            result = {"status": "success", "doc_id": doc_id, "metadata": document_metadata}
            self._cache[cache_key] = (result, time.time())
            
            # CLI140f: Cleanup old cache entries (simple LRU)
            if len(self._cache) > 100:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]

            latency = time.time() - start_time
            logger.debug(f"Document metadata saved for {doc_id} in {latency:.3f}s")
            
            return result

        except asyncio.TimeoutError:
            logger.warning(f"Firestore save timeout for document {doc_id}")
            return {"status": "timeout", "doc_id": doc_id, "error": "Firestore timeout"}
        except Exception as e:
            logger.error(f"Failed to save document metadata for {doc_id}: {e}")
            return {"status": "failed", "doc_id": doc_id, "error": str(e)}

    async def ingest_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        save_to_disk: bool = True,
        save_dir: str = "saved_documents"
    ) -> Dict[str, Any]:
        """
        Ingest a single document with performance optimization.
        CLI140f: Target <0.3s per call.
        """
        start_time = time.time()
        
        try:
            await self._ensure_initialized()
            
            # CLI140f: Parallel execution of disk save and metadata save
            tasks = []
            
            # Task 1: Save to disk (if enabled)
            if save_to_disk:
                tasks.append(self._save_to_disk(doc_id, content, save_dir))
            
            # Task 2: Save metadata to Firestore
            tasks.append(self._save_document_metadata(doc_id, content, metadata))
            
            # CLI140f: Execute tasks concurrently with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=0.25  # 250ms total timeout
            )
            
            # Process results
            disk_result = None
            metadata_result = None
            
            if save_to_disk:
                disk_result = results[0] if not isinstance(results[0], Exception) else {"status": "failed", "error": str(results[0])}
                metadata_result = results[1] if not isinstance(results[1], Exception) else {"status": "failed", "error": str(results[1])}
            else:
                metadata_result = results[0] if not isinstance(results[0], Exception) else {"status": "failed", "error": str(results[0])}

            # CLI140f: Update performance metrics
            latency = time.time() - start_time
            self._performance_metrics["total_calls"] += 1
            self._performance_metrics["total_time"] += latency
            self._performance_metrics["avg_latency"] = self._performance_metrics["total_time"] / self._performance_metrics["total_calls"]

            result = {
                "status": "success" if metadata_result.get("status") == "success" else "partial",
                "doc_id": doc_id,
                "latency": latency,
                "metadata_result": metadata_result,
                "disk_result": disk_result if save_to_disk else None,
                "performance_target_met": latency < 0.3
            }
            
            logger.info(f"Document {doc_id} ingested in {latency:.3f}s (target: <0.3s)")
            return result

        except asyncio.TimeoutError:
            latency = time.time() - start_time
            logger.warning(f"Document ingestion timeout for {doc_id} after {latency:.3f}s")
            return {
                "status": "timeout",
                "doc_id": doc_id,
                "latency": latency,
                "error": "Ingestion timeout",
                "performance_target_met": False
            }
        except Exception as e:
            latency = time.time() - start_time
            logger.error(f"Document ingestion failed for {doc_id}: {e}")
            return {
                "status": "failed",
                "doc_id": doc_id,
                "latency": latency,
                "error": str(e),
                "performance_target_met": False
            }

    async def _save_to_disk(self, doc_id: str, content: str, save_dir: str) -> Dict[str, Any]:
        """Save document to disk asynchronously."""
        try:
            # CLI140f: Use thread pool for disk I/O to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _sync_save():
                import os
                os.makedirs(save_dir, exist_ok=True)
                filename = f"{doc_id}.txt"
                file_path = os.path.join(save_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return file_path

            file_path = await loop.run_in_executor(None, _sync_save)
            return {"status": "success", "file_path": file_path}
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def batch_ingest_documents(
        self,
        documents: List[Dict[str, Any]],
        save_to_disk: bool = True,
        save_dir: str = "saved_documents"
    ) -> Dict[str, Any]:
        """
        Batch ingest documents with performance optimization.
        CLI140f: Target <5s for 100 documents.
        """
        start_time = time.time()
        
        try:
            await self._ensure_initialized()
            
            if not documents:
                return {"status": "failed", "error": "No documents provided", "results": []}

            # CLI140f: Process in optimized batches
            batch_size = min(self._batch_size, len(documents))
            results = []
            
            # CLI140f: Process documents in concurrent batches
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_start = time.time()
                
                # Create tasks for concurrent processing
                tasks = []
                for doc in batch:
                    doc_id = doc.get("doc_id")
                    content = doc.get("content", "")
                    metadata = doc.get("metadata", {})
                    
                    if not doc_id or not content:
                        results.append({
                            "status": "failed",
                            "doc_id": doc_id or "unknown",
                            "error": "Missing doc_id or content"
                        })
                        continue
                    
                    task = self.ingest_document(doc_id, content, metadata, save_to_disk, save_dir)
                    tasks.append(task)
                
                # CLI140f: Execute batch with timeout
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
                        else:
                            results.append(result)
                            
                except asyncio.TimeoutError:
                    logger.warning(f"Batch timeout for documents {i}-{i+batch_size}")
                    for j in range(len(tasks)):
                        results.append({
                            "status": "timeout",
                            "doc_id": batch[j].get("doc_id", "unknown"),
                            "error": "Batch timeout"
                        })
                
                batch_latency = time.time() - batch_start
                logger.debug(f"Processed batch {i//batch_size + 1} in {batch_latency:.3f}s")

            # CLI140f: Update batch performance metrics
            total_latency = time.time() - start_time
            self._performance_metrics["batch_calls"] += 1
            self._performance_metrics["batch_time"] += total_latency

            # Calculate success metrics
            successful = sum(1 for r in results if r.get("status") == "success")
            failed = len(results) - successful
            
            performance_target_met = total_latency < 5.0 and len(documents) <= 100
            
            result = {
                "status": "completed",
                "total_documents": len(documents),
                "successful": successful,
                "failed": failed,
                "total_latency": total_latency,
                "avg_latency_per_doc": total_latency / len(documents) if documents else 0,
                "performance_target_met": performance_target_met,
                "results": results,
                "performance_metrics": self._performance_metrics.copy()
            }
            
            logger.info(f"Batch ingestion completed: {successful}/{len(documents)} successful in {total_latency:.3f}s")
            return result

        except Exception as e:
            total_latency = time.time() - start_time
            logger.error(f"Batch ingestion failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "total_latency": total_latency,
                "performance_target_met": False,
                "results": []
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()

    def reset_performance_metrics(self):
        """Reset performance metrics."""
        self._performance_metrics = {
            "total_calls": 0,
            "total_time": 0.0,
            "avg_latency": 0.0,
            "batch_calls": 0,
            "batch_time": 0.0
        }


# Global instance
_document_ingestion_tool = None


def get_document_ingestion_tool() -> DocumentIngestionTool:
    """Get or create the global document ingestion tool instance."""
    global _document_ingestion_tool
    if _document_ingestion_tool is None:
        _document_ingestion_tool = DocumentIngestionTool()
    return _document_ingestion_tool


# Async API functions
async def ingest_document(
    doc_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    save_to_disk: bool = True,
    save_dir: str = "saved_documents"
) -> Dict[str, Any]:
    """
    Ingest a single document with performance optimization.
    CLI140f: Target <0.3s per call.
    """
    tool = get_document_ingestion_tool()
    return await tool.ingest_document(doc_id, content, metadata, save_to_disk, save_dir)


async def batch_ingest_documents(
    documents: List[Dict[str, Any]],
    save_to_disk: bool = True,
    save_dir: str = "saved_documents"
) -> Dict[str, Any]:
    """
    Batch ingest documents with performance optimization.
    CLI140f: Target <5s for 100 documents.
    """
    tool = get_document_ingestion_tool()
    return await tool.batch_ingest_documents(documents, save_to_disk, save_dir)


# Sync wrapper for compatibility
def ingest_document_sync(
    doc_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    save_to_disk: bool = True,
    save_dir: str = "saved_documents"
) -> Dict[str, Any]:
    """Synchronous wrapper for document ingestion."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    ingest_document(doc_id, content, metadata, save_to_disk, save_dir)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                ingest_document(doc_id, content, metadata, save_to_disk, save_dir)
            )
    except Exception as e:
        return {
            "status": "failed",
            "doc_id": doc_id,
            "error": str(e),
            "performance_target_met": False
        } 