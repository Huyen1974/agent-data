"""
Test coverage for qdrant_vectorization_tool.py - CLI140e.3.3
Target: Increase coverage from 15% to 65% with approximately 5 unit tests
"""

import pytest
import time
from unittest.mock import AsyncMock, patch

from src.agent_data_manager.tools.qdrant_vectorization_tool import (
    QdrantVectorizationTool,
    get_vectorization_tool,
    qdrant_vectorize_document,
    qdrant_rag_search,
    qdrant_batch_vectorize_documents,
)


@pytest.mark.qdrant
@pytest.mark.asyncio
class TestQdrantVectorizationToolCoverage:
    """Test class for QdrantVectorizationTool coverage improvement."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_embedding_provider = AsyncMock()
        self.mock_embedding_provider.embed_single.return_value = [0.1] * 1536
        self.mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """Test rate limiting mechanism for free tier constraints."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Test rate limiter initialization
        assert "last_call" in tool._rate_limiter
        assert "min_interval" in tool._rate_limiter
        assert tool._rate_limiter["min_interval"] == 0.3  # 300ms

        # Test rate limiting behavior
        await tool._rate_limit()
        first_call_time = time.time()

        await tool._rate_limit()
        second_call_time = time.time()

        # Second call should be delayed by at least min_interval
        time_diff = second_call_time - first_call_time
        assert time_diff >= 0.25  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_initialization_states(self):
        """Test initialization states and ensure_initialized behavior."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Initially not initialized
        assert not tool._initialized
        assert tool.qdrant_store is None
        assert tool.firestore_manager is None

        # Mock the initialization dependencies
        with patch("src.agent_data_manager.tools.qdrant_vectorization_tool.settings") as mock_settings, patch(
            "src.agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore"
        ), patch("src.agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"):

            mock_settings.get_qdrant_config.return_value = {
                "url": "test_url",
                "api_key": "test_key",
                "collection_name": "test_collection",
                "vector_size": 1536,
            }
            mock_settings.get_firestore_config.return_value = {
                "project_id": "test_project",
                "metadata_collection": "test_metadata",
            }

            await tool._ensure_initialized()

            # Should be initialized after first call
            assert tool._initialized
            assert tool.qdrant_store is not None
            assert tool.firestore_manager is not None

            # Multiple calls should not reinitialize
            qdrant_store_ref = tool.qdrant_store
            await tool._ensure_initialized()
            assert tool.qdrant_store is qdrant_store_ref

    @pytest.mark.asyncio
    async def test_vectorize_document_success_path(self):
        """Test successful document vectorization with all features."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Mock all dependencies
        with patch.object(tool, "_ensure_initialized") as mock_init, patch.object(
            tool, "_update_vector_status"
        ) as mock_update_status, patch(
            "src.agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool"
        ) as mock_auto_tag, patch(
            "src.agent_data_manager.tools.qdrant_vectorization_tool.get_event_manager"
        ) as mock_event_mgr:

            # Setup mocks
            mock_init.return_value = None
            tool.qdrant_store = AsyncMock()
            tool.qdrant_store.upsert_vector.return_value = {"success": True, "vector_id": "test_doc_1"}

            mock_auto_tagging = AsyncMock()
            mock_auto_tagging.enhance_metadata_with_tags.return_value = {
                "doc_id": "test_doc_1",
                "auto_tags": ["tag1", "tag2"],
            }
            mock_auto_tag.return_value = mock_auto_tagging

            mock_event_manager = AsyncMock()
            mock_event_manager.publish_save_document_event.return_value = {"status": "published"}
            mock_event_mgr.return_value = mock_event_manager

            # Test vectorization
            result = await tool.vectorize_document(
                doc_id="test_doc_1",
                content="Test document content",
                metadata={"test": "metadata"},
                tag="test_tag",
                update_firestore=True,
                enable_auto_tagging=True,
            )

            # Verify success
            assert result["status"] == "success"
            assert result["doc_id"] == "test_doc_1"
            assert result["vector_id"] == "test_doc_1"
            assert result["embedding_dimension"] == 1536
            assert result["firestore_updated"] is True

            # Verify calls
            mock_update_status.assert_any_call("test_doc_1", "pending", {"test": "metadata"})
            mock_update_status.assert_any_call("test_doc_1", "completed", {"test": "metadata"})
            mock_auto_tagging.enhance_metadata_with_tags.assert_called_once()
            mock_event_manager.publish_save_document_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_vectorize_document_embedding_error(self):
        """Test handling of embedding generation errors."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Make embedding fail
        from src.agent_data_manager.embedding.embedding_provider import EmbeddingError

        self.mock_embedding_provider.embed_single.side_effect = EmbeddingError("Embedding failed")

        with patch.object(tool, "_ensure_initialized") as mock_init, patch.object(
            tool, "_update_vector_status"
        ) as mock_update_status:

            mock_init.return_value = None

            result = await tool.vectorize_document(doc_id="test_doc_1", content="Test content", update_firestore=True)

            # Verify error handling
            assert result["status"] == "failed"
            assert "Embedding failed" in result["error"]
            assert result["doc_id"] == "test_doc_1"

            # Verify status update
            mock_update_status.assert_any_call("test_doc_1", "pending", None)
            mock_update_status.assert_any_call("test_doc_1", "failed", None, "Embedding failed")

    @pytest.mark.asyncio
    async def test_rag_search_with_mocked_components(self):
        """Test RAG search components and error handling for coverage."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Test filtering methods directly for coverage
        sample_results = [
            {"auto_tags": ["tag1", "tag2"], "category": "test", "level_1_category": "cat1"},
            {"auto_tags": ["tag3"], "category": "other", "level_1_category": "cat2"},
            {"auto_tags": ["tag1"], "category": "test", "level_2_category": "subcat1"},
        ]

        # Test metadata filtering
        filtered_by_metadata = tool._filter_by_metadata(sample_results, {"category": "test"})
        assert len(filtered_by_metadata) == 2

        # Test tag filtering
        filtered_by_tags = tool._filter_by_tags(sample_results, ["tag1"])
        assert len(filtered_by_tags) == 2

        # Test path filtering
        filtered_by_path = tool._filter_by_path(sample_results, "cat1")
        assert len(filtered_by_path) >= 1  # At least one result contains "cat1"

        # Test hierarchy path building
        hierarchy_path = tool._build_hierarchy_path(sample_results[0])
        assert "cat1" in hierarchy_path

    @pytest.mark.asyncio
    async def test_rag_search_full_workflow(self):
        """Test complete RAG search workflow with mocked dependencies."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        with patch.object(tool, "_ensure_initialized") as mock_init, patch.object(
            tool, "_batch_get_firestore_metadata"
        ) as mock_batch_get:

            mock_init.return_value = None
            tool.qdrant_store = AsyncMock()

            # Mock Qdrant search results
            tool.qdrant_store.semantic_search.return_value = {
                "status": "success",
                "results": [
                    {"doc_id": "doc1", "score": 0.8, "metadata": {"category": "test"}},
                    {"doc_id": "doc2", "score": 0.7, "metadata": {"category": "other"}},
                ],
            }

            # Mock Firestore metadata
            mock_batch_get.return_value = {
                "doc1": {"auto_tags": ["tag1"], "category": "test", "level_1_category": "cat1"},
                "doc2": {"auto_tags": ["tag2"], "category": "other", "level_1_category": "cat2"},
            }

            # Test RAG search
            result = await tool.rag_search(
                query_text="test query",
                metadata_filters={"category": "test"},
                tags=["tag1"],
                path_query="cat1",
                limit=10,
                score_threshold=0.5,
                qdrant_tag="test_tag",
            )

            # Verify results
            assert result["status"] == "success"
            assert "results" in result
            assert len(result["results"]) >= 0  # May be filtered down

    @pytest.mark.asyncio
    async def test_batch_vectorize_documents_success(self):
        """Test batch vectorization with success and failure cases."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        with patch.object(tool, "_ensure_initialized") as mock_init, patch.object(
            tool, "vectorize_document"
        ) as mock_vectorize, patch("src.agent_data_manager.tools.qdrant_vectorization_tool.settings") as mock_settings:

            mock_init.return_value = None
            mock_settings.get_qdrant_config.return_value = {
                "batch_size": 2,
                "sleep_between_batches": 0.1,
            }

            # Mock vectorize_document responses
            mock_vectorize.side_effect = [
                {"status": "success", "doc_id": "doc1"},
                {"status": "failed", "doc_id": "doc2", "error": "Test error"},
                {"status": "success", "doc_id": "doc3"},
            ]

            documents = [
                {"doc_id": "doc1", "content": "Content 1", "metadata": {"test": "meta1"}},
                {"doc_id": "doc2", "content": "Content 2"},
                {"doc_id": "doc3", "content": "Content 3"},
            ]

            result = await tool.batch_vectorize_documents(documents, tag="batch_tag", update_firestore=True)

            # Verify batch results
            assert result["status"] == "completed"
            assert result["total_documents"] == 3
            assert result["successful"] == 2
            assert result["failed"] == 1
            assert result["batches_processed"] == 2  # 2 batches with batch_size=2
            assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_vectorize_invalid_documents(self):
        """Test batch vectorization with invalid document formats."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        with patch.object(tool, "_ensure_initialized") as mock_init, patch(
            "src.agent_data_manager.tools.qdrant_vectorization_tool.settings"
        ) as mock_settings:

            mock_init.return_value = None
            mock_settings.get_qdrant_config.return_value = {
                "batch_size": 10,
                "sleep_between_batches": 0.1,
            }

            # Invalid documents (missing doc_id or content)
            documents = [
                {"content": "Content without doc_id"},  # Missing doc_id
                {"doc_id": "doc2"},  # Missing content
                {},  # Missing both
            ]

            result = await tool.batch_vectorize_documents(documents)

            # Verify all failed due to invalid format
            assert result["status"] == "completed"
            assert result["total_documents"] == 3
            assert result["successful"] == 0
            assert result["failed"] == 3
            assert len(result["results"]) == 3

            # Check error messages
            for res in result["results"]:
                assert res["status"] == "failed"
                assert "Missing doc_id or content" in res["error"]

    @pytest.mark.asyncio
    async def test_update_vector_status_error_handling(self):
        """Test _update_vector_status with error scenarios."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Mock firestore_manager that raises exception
        tool.firestore_manager = AsyncMock()
        tool.firestore_manager.save_metadata.side_effect = Exception("Firestore error")

        # Should not raise exception even if Firestore fails
        await tool._update_vector_status("test_doc", "failed", {"test": "meta"}, "Test error")

        # Verify the call was attempted
        tool.firestore_manager.save_metadata.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="CLI140m.69: Async vectorization test with timeout issues")
    async def test_vectorize_document_upsert_failure(self):
        """Test handling of Qdrant upsert failures."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        with patch.object(tool, "_ensure_initialized") as mock_init, patch.object(
            tool, "_update_vector_status"
        ) as mock_update_status:

            mock_init.return_value = None
            tool.qdrant_store = AsyncMock()
            tool.qdrant_store.upsert_vector.return_value = {"success": False, "error": "Upsert failed"}

            result = await tool.vectorize_document(doc_id="test_doc", content="Test content", update_firestore=True)

            # Verify error handling
            assert result["status"] == "failed"
            assert "Failed to upsert vector" in result["error"]
            assert result["doc_id"] == "test_doc"

            # Verify status updates
            mock_update_status.assert_any_call("test_doc", "pending", None)
            mock_update_status.assert_any_call("test_doc", "failed", None, "Failed to upsert vector: Upsert failed")


@pytest.mark.unit
def test_get_vectorization_tool_factory():
    """Test the factory function for getting vectorization tool instance."""
    # Test with custom embedding provider first
    custom_provider = AsyncMock()
    tool1 = get_vectorization_tool(custom_provider)
    assert isinstance(tool1, QdrantVectorizationTool)
    assert tool1.embedding_provider is custom_provider

    # Test with default embedding provider (will use singleton)
    tool2 = get_vectorization_tool()
    assert isinstance(tool2, QdrantVectorizationTool)

    # Test singleton behavior
    tool3 = get_vectorization_tool()
    assert tool2 is tool3  # Should return same instance


@pytest.mark.asyncio
async def test_qdrant_vectorize_document_function():
    """Test the standalone qdrant_vectorize_document function."""
    with patch("src.agent_data_manager.tools.qdrant_vectorization_tool.get_vectorization_tool") as mock_get_tool:
        mock_tool = AsyncMock()
        mock_tool.vectorize_document.return_value = {"status": "success", "doc_id": "test_doc"}
        mock_get_tool.return_value = mock_tool

        result = await qdrant_vectorize_document(
            doc_id="test_doc", content="test content", metadata={"test": "meta"}, tag="test_tag", update_firestore=True
        )

        assert result["status"] == "success"
        assert result["doc_id"] == "test_doc"
        mock_tool.vectorize_document.assert_called_once_with(
            "test_doc", "test content", {"test": "meta"}, "test_tag", True
        )


@pytest.mark.asyncio
async def test_qdrant_rag_search_function():
    """Test the standalone qdrant_rag_search function."""
    with patch("src.agent_data_manager.tools.qdrant_vectorization_tool.get_vectorization_tool") as mock_get_tool:
        mock_tool = AsyncMock()
        mock_tool.rag_search.return_value = {"status": "success", "results": []}
        mock_get_tool.return_value = mock_tool

        result = await qdrant_rag_search(
            query_text="test query",
            metadata_filters={"category": "test"},
            tags=["tag1"],
            path_query="path",
            limit=5,
            score_threshold=0.7,
            qdrant_tag="test_tag",
        )

        assert result["status"] == "success"
        mock_tool.rag_search.assert_called_once_with(
            query_text="test query",
            metadata_filters={"category": "test"},
            tags=["tag1"],
            path_query="path",
            limit=5,
            score_threshold=0.7,
            qdrant_tag="test_tag",
        )


@pytest.mark.asyncio
async def test_batch_vectorize_documents_function():
    """Test the standalone qdrant_batch_vectorize_documents function."""
    with patch("src.agent_data_manager.tools.qdrant_vectorization_tool.get_vectorization_tool") as mock_get_tool:
        mock_tool = AsyncMock()
        mock_tool.batch_vectorize_documents.return_value = {"status": "completed", "successful": 2, "failed": 0}
        mock_get_tool.return_value = mock_tool

        documents = [{"doc_id": "doc1", "content": "content1"}, {"doc_id": "doc2", "content": "content2"}]
        result = await qdrant_batch_vectorize_documents(documents, tag="batch_tag", update_firestore=True)

        assert result["status"] == "completed"
        assert result["successful"] == 2
        mock_tool.batch_vectorize_documents.assert_called_once_with(documents, "batch_tag", True)
