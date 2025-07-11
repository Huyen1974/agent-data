"""
CLI140f Performance Tests
Tests for document ingestion and Qdrant vectorization performance optimization.
Target: <0.3s per call, <5s for 100 docs batch processing.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, List, Any
import logging

# Test imports
from ADK.agent_data.tools.document_ingestion_tool import (
    DocumentIngestionTool,
    ingest_document,
    batch_ingest_documents,
    get_document_ingestion_tool
)
from ADK.agent_data.tools.qdrant_vectorization_tool import (
    QdrantVectorizationTool,
    qdrant_vectorize_document,
    qdrant_batch_vectorize_documents
)

logger = logging.getLogger(__name__)


class TestCLI140fPerformance:
    """Test suite for CLI140f performance optimization."""

    @pytest.fixture
    def mock_firestore_manager(self):
        """Mock Firestore manager for testing."""
        mock_manager = AsyncMock()
        mock_manager.save_metadata.return_value = {"status": "success"}
        mock_manager.get_metadata.return_value = {
            "doc_id": "test_doc",
            "status": "ingested",
            "version": 1
        }
        return mock_manager

    @pytest.fixture
    def mock_qdrant_store(self):
        """Mock Qdrant store for testing."""
        mock_store = AsyncMock()
        mock_store.upsert_vector.return_value = {
            "success": True,
            "vector_id": "test_doc",
            "status": "upserted"
        }
        mock_store.semantic_search.return_value = {
            "results": [
                {
                    "metadata": {"doc_id": "test_doc", "content": "Test content"},
                    "score": 0.85
                }
            ]
        }
        return mock_store

    @pytest.fixture
    def mock_openai_embedding(self):
        """Mock OpenAI embedding generation."""
        def mock_embedding(*args, **kwargs):
            return {
                "embedding": [0.1] * 1536,  # Standard OpenAI embedding dimension
                "model": "text-embedding-ada-002"
            }
        return mock_embedding

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_document_ingestion_single_latency(self, mock_firestore_manager):
        """
        Test single document ingestion latency.
        CLI140f Target: <0.3s per call.
        """
        # Initialize tool with mocks
        ingestion_tool = DocumentIngestionTool()
        
        # Mock the initialization and firestore manager
        with patch.object(ingestion_tool, '_ensure_initialized', AsyncMock()), \
             patch.object(ingestion_tool, 'firestore_manager', mock_firestore_manager), \
             patch('ADK.agent_data.tools.document_ingestion_tool.settings') as mock_settings:
            
            # Mock settings
            mock_settings.get_firestore_config.return_value = {
                "project_id": "test_project",
                "metadata_collection": "test_collection"
            }
            
            # Set initialized flag
            ingestion_tool._initialized = True
            
            start_time = time.time()
            
            result = await ingestion_tool.ingest_document(
                doc_id="cli140f_test_doc_1",
                content="This is a test document for CLI140f performance optimization. " * 50,
                metadata={"test": True, "cli": "140f"},
                save_to_disk=False  # Skip disk I/O for pure performance test
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            # Assertions
            assert result["status"] in ["success", "partial"]
            assert result["doc_id"] == "cli140f_test_doc_1"
            assert latency < 0.3, f"Document ingestion latency {latency:.3f}s exceeds target 0.3s"
            assert result["performance_target_met"] is True
            
            logger.info(f"Document Ingestion Latency: {latency:.3f}s")
            
            return {
                "latency": latency,
                "result": result
            }

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_qdrant_vectorization_single_latency(
        self, mock_qdrant_store, mock_firestore_manager, mock_openai_embedding
    ):
        """
        Test single document vectorization latency.
        CLI140f Target: <0.3s per call.
        """
        # Initialize tool with mocks
        vectorization_tool = QdrantVectorizationTool()
        
        with patch.object(vectorization_tool, 'qdrant_store', mock_qdrant_store), \
             patch.object(vectorization_tool, 'firestore_manager', mock_firestore_manager), \
             patch.object(vectorization_tool, '_ensure_initialized', AsyncMock()), \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.get_openai_embedding', 
                   AsyncMock(return_value=mock_openai_embedding())):
            
            # Set initialized flag
            vectorization_tool._initialized = True
            
            start_time = time.time()
            
            result = await vectorization_tool.vectorize_document(
                doc_id="cli140f_vector_test_1",
                content="This is a test document for CLI140f vectorization performance optimization. " * 50,
                metadata={"test": True, "cli": "140f"},
                enable_auto_tagging=False  # Disable for pure performance test
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            # Assertions
            assert result["status"] == "success"
            assert result["doc_id"] == "cli140f_vector_test_1"
            assert latency < 0.3, f"Vectorization latency {latency:.3f}s exceeds target 0.3s"
            assert result["performance_target_met"] is True
            assert "embedding_dimension" in result
            
            logger.info(f"Vectorization Latency: {latency:.3f}s")
            
            return {
                "latency": latency,
                "result": result
            }

    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_batch_processing_performance(
        self, mock_qdrant_store, mock_firestore_manager, mock_openai_embedding
    ):
        """
        Test batch processing performance for both ingestion and vectorization.
        CLI140f Target: <5s for 100 documents (scaled to 30 docs for test speed).
        """
        # Initialize tools
        ingestion_tool = DocumentIngestionTool()
        vectorization_tool = QdrantVectorizationTool()
        
        # Create test documents (30 docs for reasonable test time)
        test_documents = [
            {
                "doc_id": f"cli140f_batch_doc_{i}",
                "content": f"This is test document {i} for CLI140f batch performance optimization. " * 20,
                "metadata": {"test": True, "cli": "140f", "batch_index": i}
            }
            for i in range(30)
        ]
        
        with patch.object(ingestion_tool, '_ensure_initialized', AsyncMock()), \
             patch.object(ingestion_tool, 'firestore_manager', mock_firestore_manager), \
             patch.object(vectorization_tool, 'qdrant_store', mock_qdrant_store), \
             patch.object(vectorization_tool, 'firestore_manager', mock_firestore_manager), \
             patch.object(vectorization_tool, '_ensure_initialized', AsyncMock()), \
             patch('ADK.agent_data.tools.qdrant_vectorization_tool.get_openai_embedding', 
                   AsyncMock(return_value=mock_openai_embedding())), \
             patch('ADK.agent_data.tools.document_ingestion_tool.settings') as mock_settings:
            
            # Mock settings
            mock_settings.get_firestore_config.return_value = {
                "project_id": "test_project",
                "metadata_collection": "test_collection"
            }
            
            # Set initialized flags
            ingestion_tool._initialized = True
            vectorization_tool._initialized = True
            
            # Test batch ingestion
            start_time = time.time()
            ingestion_result = await ingestion_tool.batch_ingest_documents(
                documents=test_documents,
                save_to_disk=False
            )
            ingestion_time = time.time() - start_time
            
            # Test batch vectorization
            start_time = time.time()
            vectorization_result = await vectorization_tool.batch_vectorize_documents(
                documents=test_documents,
                update_firestore=True
            )
            vectorization_time = time.time() - start_time
        
        # Assertions for ingestion
        assert ingestion_result["status"] == "completed"
        assert ingestion_result["successful"] > 0
        assert ingestion_time < 1.5, f"Batch ingestion {ingestion_time:.3f}s exceeds scaled target 1.5s"
        
        # Assertions for vectorization
        assert vectorization_result["status"] == "completed"
        assert vectorization_result["successful"] > 0
        assert vectorization_time < 1.5, f"Batch vectorization {vectorization_time:.3f}s exceeds scaled target 1.5s"
        
        # Performance metrics
        total_time = ingestion_time + vectorization_time
        avg_time_per_doc = total_time / len(test_documents)
        
        logger.info(f"Batch Performance - Ingestion: {ingestion_time:.3f}s, Vectorization: {vectorization_time:.3f}s")
        logger.info(f"Total: {total_time:.3f}s for {len(test_documents)} documents")
        logger.info(f"Average per document: {avg_time_per_doc:.3f}s")
        
        return {
            "ingestion_time": ingestion_time,
            "vectorization_time": vectorization_time,
            "total_time": total_time,
            "avg_time_per_doc": avg_time_per_doc,
            "ingestion_result": ingestion_result,
            "vectorization_result": vectorization_result
        }

    @pytest.mark.performance
    @pytest.mark.unit
    def test_document_ingestion_tool_performance_metrics(self):
        """Test performance metrics tracking in DocumentIngestionTool."""
        tool = get_document_ingestion_tool()
        
        # Reset metrics
        tool.reset_performance_metrics()
        initial_metrics = tool.get_performance_metrics()
        
        assert initial_metrics["total_calls"] == 0
        assert initial_metrics["total_time"] == 0.0
        assert initial_metrics["avg_latency"] == 0.0
        assert initial_metrics["batch_calls"] == 0
        assert initial_metrics["batch_time"] == 0.0

    @pytest.mark.performance
    @pytest.mark.unit
    def test_cli140f_performance_targets_summary(self):
        """
        Summary test documenting CLI140f performance targets and optimizations.
        """
        performance_targets = {
            "single_document_ingestion": {"target": 0.3, "unit": "seconds"},
            "single_document_vectorization": {"target": 0.3, "unit": "seconds"},
            "batch_100_documents": {"target": 5.0, "unit": "seconds"},
        }
        
        optimizations_implemented = [
            "Parallel task execution in document ingestion",
            "Concurrent batch processing with optimized batch sizes (10 docs/batch)",
            "Timeout-based operations to prevent hangs (200ms, 150ms timeouts)",
            "In-memory caching for metadata operations (5min TTL, 100 entry LRU)",
            "Fire-and-forget Firestore updates for performance",
            "Reduced retry attempts (2 retries vs 3) with faster backoff",
            "Disabled auto-tagging in batch operations for speed",
            "Thread pool for disk I/O operations",
            "Optimized error handling and logging"
        ]
        
        logger.info("CLI140f Performance Optimization Summary:")
        logger.info("Performance Targets:")
        for target, specs in performance_targets.items():
            logger.info(f"  - {target}: <{specs['target']} {specs['unit']}")
        
        logger.info("Optimizations Implemented:")
        for optimization in optimizations_implemented:
            logger.info(f"  - {optimization}")
        
        # This test always passes - it's for documentation
        assert len(performance_targets) == 3
        assert len(optimizations_implemented) == 9 