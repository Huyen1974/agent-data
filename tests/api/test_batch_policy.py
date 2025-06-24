"""Tests for batch processing policy validation in qdrant_vectorization_tool."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch

from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool
from agent_data_manager.config.settings import settings


class TestBatchPolicy:
    """Test batch processing policy enforcement."""

    @pytest.fixture
    def mock_vectorization_tool(self):
        """Create a mock vectorization tool for testing."""
        tool = QdrantVectorizationTool()
        tool._initialized = True
        tool.qdrant_store = AsyncMock()
        tool.firestore_manager = AsyncMock()
        return tool

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for batch testing."""
        return [
            {
                "doc_id": f"test_doc_{i}",
                "content": f"Test content for document {i}",
                "metadata": {"test": True, "index": i},
            }
            for i in range(25)  # 25 documents to test batching
        ]

    @pytest.mark.asyncio
    async def test_batch_size_enforcement(self, mock_vectorization_tool, sample_documents):
        """Test that batch processing respects the configured batch size."""

        # Mock the vectorize_document method to track calls
        mock_vectorization_tool.vectorize_document = AsyncMock(return_value={"status": "success", "doc_id": "test"})

        # Override batch size for testing
        with patch.object(settings, "get_qdrant_config") as mock_config:
            mock_config.return_value = {"batch_size": 10, "sleep_between_batches": 0.01}  # Very short sleep for testing

            result = await mock_vectorization_tool.batch_vectorize_documents(
                documents=sample_documents, tag="test_batch", update_firestore=False
            )

            # Verify batch processing results
            assert result["status"] == "completed"
            assert result["total_documents"] == 25
            assert result["successful"] == 25
            assert result["failed"] == 0
            assert result["batch_size"] == 10
            assert result["batches_processed"] == 3  # 25 docs / 10 batch_size = 3 batches

            # Verify that vectorize_document was called for each document
            assert mock_vectorization_tool.vectorize_document.call_count == 25

    @pytest.mark.asyncio
    async def test_sleep_between_batches(self, mock_vectorization_tool, sample_documents):
        """Test that sleep is applied between batches but not after the last batch."""

        # Mock the vectorize_document method
        mock_vectorization_tool.vectorize_document = AsyncMock(return_value={"status": "success", "doc_id": "test"})

        # Track sleep calls
        sleep_calls = []
        original_sleep = asyncio.sleep

        async def mock_sleep(duration):
            sleep_calls.append(duration)
            await original_sleep(0.001)  # Very short actual sleep for testing

        with patch.object(settings, "get_qdrant_config") as mock_config, patch("asyncio.sleep", side_effect=mock_sleep):

            mock_config.return_value = {"batch_size": 10, "sleep_between_batches": 0.35}

            result = await mock_vectorization_tool.batch_vectorize_documents(
                documents=sample_documents, tag="test_batch", update_firestore=False
            )

            # Verify results
            assert result["status"] == "completed"
            assert result["batches_processed"] == 3
            assert result["sleep_between_batches"] == 0.35

            # Verify sleep calls - should be called between batches but not after the last batch
            # With 25 docs and batch_size 10: batches are [0-9], [10-19], [20-24]
            # Sleep should occur after batch 1 and batch 2, but not after batch 3
            batch_sleep_calls = [call for call in sleep_calls if call == 0.35]
            assert len(batch_sleep_calls) == 2  # Sleep between batch 1-2 and 2-3, not after 3

    @pytest.mark.asyncio
    async def test_rate_limit_applied_per_document(self, mock_vectorization_tool, sample_documents):
        """Test that rate limiting is applied per document."""

        # Mock the rate_limit method to track calls
        rate_limit_calls = []

        async def mock_rate_limit():
            rate_limit_calls.append(time.time())
            await asyncio.sleep(0.001)  # Very short sleep for testing

        mock_vectorization_tool._rate_limit = mock_rate_limit
        mock_vectorization_tool.vectorize_document = AsyncMock(return_value={"status": "success", "doc_id": "test"})

        with patch.object(settings, "get_qdrant_config") as mock_config:
            mock_config.return_value = {"batch_size": 10, "sleep_between_batches": 0.01}

            result = await mock_vectorization_tool.batch_vectorize_documents(
                documents=sample_documents[:5],  # Use fewer documents for faster test
                tag="test_batch",
                update_firestore=False,
            )

            # Verify that rate limiting was called for each document
            assert len(rate_limit_calls) == 5
            assert result["total_documents"] == 5

    @pytest.mark.asyncio
    async def test_batch_policy_with_failures(self, mock_vectorization_tool, sample_documents):
        """Test batch processing behavior when some documents fail."""

        # Mock vectorize_document to return failures for some documents
        async def mock_vectorize_with_failures(doc_id, content, metadata=None, tag=None, update_firestore=True):
            # Fail every 3rd document
            if int(doc_id.split("_")[-1]) % 3 == 0:
                return {"status": "failed", "error": "Simulated failure", "doc_id": doc_id}
            else:
                return {"status": "success", "doc_id": doc_id}

        mock_vectorization_tool.vectorize_document = mock_vectorize_with_failures

        with patch.object(settings, "get_qdrant_config") as mock_config:
            mock_config.return_value = {"batch_size": 5, "sleep_between_batches": 0.01}

            result = await mock_vectorization_tool.batch_vectorize_documents(
                documents=sample_documents[:10], tag="test_batch", update_firestore=False  # Use 10 documents
            )

            # Verify results
            assert result["status"] == "completed"
            assert result["total_documents"] == 10
            assert result["batches_processed"] == 2
            # Documents 0, 3, 6, 9 should fail (4 failures), rest should succeed
            assert result["failed"] == 4
            assert result["successful"] == 6

    @pytest.mark.asyncio
    async def test_empty_documents_list(self, mock_vectorization_tool):
        """Test batch processing with empty documents list."""

        with patch.object(settings, "get_qdrant_config") as mock_config:
            mock_config.return_value = {"batch_size": 10, "sleep_between_batches": 0.35}

            result = await mock_vectorization_tool.batch_vectorize_documents(
                documents=[], tag="test_batch", update_firestore=False
            )

            # Verify results
            assert result["status"] == "completed"
            assert result["total_documents"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0
            assert result["batches_processed"] == 0

    @pytest.mark.asyncio
    async def test_default_batch_configuration(self, mock_vectorization_tool, sample_documents):
        """Test that default batch configuration values are used when not specified."""

        mock_vectorization_tool.vectorize_document = AsyncMock(return_value={"status": "success", "doc_id": "test"})

        # Don't mock get_qdrant_config to test defaults
        result = await mock_vectorization_tool.batch_vectorize_documents(
            documents=sample_documents[:5], tag="test_batch", update_firestore=False
        )

        # Verify that default values are used
        assert result["batch_size"] == 100  # Default from settings
        assert result["sleep_between_batches"] == 0.35  # Default from settings
        assert result["batches_processed"] == 1  # 5 docs fit in one batch of 100
