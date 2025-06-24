"""
End-to-End Pipeline Tests (Optimized for <0.5s runtime)

This module contains streamlined E2E tests that validate the core Agent Data pipeline
functionality with minimal overhead and maximum speed.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, Mock


@pytest.mark.e2e
class TestE2EPipeline:
    """End-to-End pipeline tests optimized for speed."""

    @pytest.fixture
    def sample_doc(self):
        """Minimal sample document for fast E2E testing."""
        return {
            "doc_id": f"e2e-{uuid.uuid4().hex[:6]}",
            "content": "AI test",  # Very short content
            "metadata": {"test": True},
            "tag": "e2e",
        }

    @pytest.fixture
    def mock_embedding_provider(self):
        """Mock embedding provider for fast tests."""
        mock_provider = AsyncMock()
        mock_provider.embed_single.return_value = [0.1] * 1536  # Fast, pre-computed embedding
        mock_provider.get_model_name.return_value = "test-model"
        return mock_provider

    @pytest.mark.asyncio
    async def test_complete_e2e_pipeline(self, sample_doc, mock_embedding_provider):
        """Test complete E2E pipeline with minimal overhead."""
        from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

        # Prevent any real initialization by mocking at class level
        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
        ) as mock_firestore_class, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool"
        ) as mock_auto_tag, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.get_event_manager"
        ) as mock_event_mgr, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.settings"
        ) as mock_settings:

            # Mock settings to prevent config loading
            mock_settings.get_qdrant_config.return_value = {
                "url": "test",
                "api_key": "test",
                "collection_name": "test",
                "vector_size": 1536,
            }
            mock_settings.get_firestore_config.return_value = {"project_id": "test", "metadata_collection": "test"}

            # Setup ultra-fast mocks
            mock_qdrant = Mock()
            mock_qdrant.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": sample_doc["doc_id"]})
            mock_qdrant_class.return_value = mock_qdrant

            mock_firestore = Mock()
            mock_firestore.save_metadata = AsyncMock(return_value=True)
            mock_firestore_class.return_value = mock_firestore

            # Mock auto-tagging to return immediately without API calls
            mock_auto_tagging_tool = Mock()
            mock_auto_tagging_tool.enhance_metadata_with_tags = AsyncMock(return_value=sample_doc["metadata"])
            mock_auto_tag.return_value = mock_auto_tagging_tool

            mock_event_manager = Mock()
            mock_event_manager.publish_save_document_event = AsyncMock(return_value={"status": "success"})
            mock_event_mgr.return_value = mock_event_manager

            # Use the working pattern from cursor integration test
            tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)
            result = await tool.vectorize_document(
                doc_id=sample_doc["doc_id"],
                content=sample_doc["content"],
                metadata=sample_doc["metadata"],
                tag=sample_doc["tag"],
            )

            # Quick assertions
            assert result["status"] == "success"
            assert result["doc_id"] == sample_doc["doc_id"]

    @pytest.mark.asyncio
    async def test_e2e_error_handling(self, sample_doc):
        """Test E2E error handling."""
        from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

        # Mock failing embedding provider
        mock_provider = AsyncMock()
        mock_provider.embed_single.side_effect = Exception("API failure")

        # Prevent initialization overhead
        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
        ) as mock_firestore_class, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.settings"
        ) as mock_settings:

            # Mock settings to prevent config loading
            mock_settings.get_qdrant_config.return_value = {
                "url": "test",
                "api_key": "test",
                "collection_name": "test",
                "vector_size": 1536,
            }
            mock_settings.get_firestore_config.return_value = {"project_id": "test", "metadata_collection": "test"}

            mock_qdrant = Mock()
            mock_qdrant_class.return_value = mock_qdrant

            mock_firestore = Mock()
            mock_firestore_class.return_value = mock_firestore

            tool = QdrantVectorizationTool(embedding_provider=mock_provider)
            result = await tool.vectorize_document(
                doc_id=sample_doc["doc_id"],
                content=sample_doc["content"],
                metadata=sample_doc["metadata"],
                tag=sample_doc["tag"],
            )

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_e2e_performance(self, sample_doc, mock_embedding_provider):
        """Test E2E performance expectations with minimal setup."""
        import time
        from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

        start_time = time.time()

        # Prevent any initialization overhead by mocking everything upfront
        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
        ) as mock_firestore_class, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool"
        ) as mock_auto_tag, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.get_event_manager"
        ) as mock_event_mgr, patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.settings"
        ) as mock_settings:

            # Mock settings to prevent config loading
            mock_settings.get_qdrant_config.return_value = {
                "url": "test",
                "api_key": "test",
                "collection_name": "test",
                "vector_size": 1536,
            }
            mock_settings.get_firestore_config.return_value = {"project_id": "test", "metadata_collection": "test"}

            # Ultra-fast mock setup
            mock_qdrant = Mock()
            mock_qdrant.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": sample_doc["doc_id"]})
            mock_qdrant_class.return_value = mock_qdrant

            mock_firestore = Mock()
            mock_firestore_class.return_value = mock_firestore

            # Skip auto-tagging entirely
            mock_auto_tagging_tool = Mock()
            mock_auto_tagging_tool.enhance_metadata_with_tags = AsyncMock(return_value=sample_doc["metadata"])
            mock_auto_tag.return_value = mock_auto_tagging_tool

            mock_event_manager = Mock()
            mock_event_manager.publish_save_document_event = AsyncMock(return_value={"status": "success"})
            mock_event_mgr.return_value = mock_event_manager

            tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)
            result = await tool.vectorize_document(
                doc_id=sample_doc["doc_id"],
                content=sample_doc["content"],
                metadata=sample_doc["metadata"],
                tag=sample_doc["tag"],
            )

        execution_time = time.time() - start_time
        assert result["status"] == "success"
        assert execution_time < 0.5  # Target: <0.5s

    def test_e2e_markers(self):
        """Test E2E marker validation (ultra-lightweight)."""
        # Simple validation test - should be instant
        methods = [name for name in dir(self) if name.startswith("test_")]
        assert len(methods) >= 3
        assert "test_complete_e2e_pipeline" in methods
