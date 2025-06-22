"""
Test case for CLI 128 metadata management enhancements.

This test validates the enhanced metadata management logic including:
- Versioning (increment version on updates)
- Hierarchy (level_1_category through level_6_category)
- Auto-tagging using LLM via auto_tagging_tool
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager


class TestCLI128MetadataManagement:
    """Test CLI 128 metadata management enhancements."""

    @pytest.fixture
    def mock_firestore_client(self):
        """Mock Firestore client for testing."""
        mock_client = MagicMock()
        mock_doc_ref = AsyncMock()
        mock_collection = MagicMock()
        mock_doc = AsyncMock()

        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_doc
        mock_doc_ref.set = AsyncMock()
        mock_client.collection.return_value = mock_collection

        return mock_client, mock_doc_ref, mock_doc

    @pytest.fixture
    def metadata_manager(self, mock_firestore_client):
        """Create FirestoreMetadataManager with mocked dependencies."""
        mock_client, mock_doc_ref, mock_doc = mock_firestore_client

        with patch("agent_data_manager.vector_store.firestore_metadata_manager.FirestoreAsyncClient") as mock_firestore:
            mock_firestore.return_value = mock_client
            manager = FirestoreMetadataManager(project_id="test-project", collection_name="test_metadata")
            manager.db = mock_client
            return manager, mock_doc_ref, mock_doc

    @pytest.fixture
    def mock_auto_tagging_tool(self):
        """Mock auto-tagging tool for testing."""
        mock_tool = AsyncMock()
        mock_tool.generate_tags.return_value = {
            "status": "success",
            "tags": ["machine learning", "artificial intelligence", "python", "neural networks", "data science"],
            "source": "openai",
            "content_hash": "test_hash_123",
            "metadata": {
                "generated_at": "2025-01-18T10:00:00Z",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        }
        return mock_tool

    async def test_comprehensive_metadata_management_logic(self, metadata_manager, mock_auto_tagging_tool):
        """
        Comprehensive test for CLI 128 metadata management enhancements.

        Tests versioning, hierarchy (level_1_category through level_6_category),
        and auto-tagging integration in a single comprehensive test.
        """
        manager, mock_doc_ref, mock_doc = metadata_manager

        # Test 1: Versioning with new document
        mock_doc.exists = False
        with patch(
            "agent_data_manager.tools.auto_tagging_tool.get_auto_tagging_tool", return_value=mock_auto_tagging_tool
        ):
            new_metadata = {
                "doc_id": "test_doc_1",
                "content": "This is a research paper about machine learning algorithms",
                "doc_type": "research_paper",
                "author": "Dr. Jane Smith",
                "year": 2025,
                "language": "english",
                "format": "pdf",
            }
            await manager.save_metadata("test_doc_1", new_metadata)

        # Verify new document versioning
        assert mock_doc_ref.set.called
        saved_metadata = mock_doc_ref.set.call_args[0][0]
        assert saved_metadata["version"] == 1
        assert "createdAt" in saved_metadata
        assert "lastUpdated" in saved_metadata

        # Verify hierarchy structure
        assert saved_metadata["level_1_category"] == "research_paper"
        assert saved_metadata["level_2_category"] == "machine learning"  # First auto-tag
        assert saved_metadata["level_3_category"] == "Dr. Jane Smith"
        assert saved_metadata["level_4_category"] == "2025"
        assert saved_metadata["level_5_category"] == "english"
        assert saved_metadata["level_6_category"] == "pdf"

        # Verify all 6 hierarchy levels are present
        for level in [
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "level_4_category",
            "level_5_category",
            "level_6_category",
        ]:
            assert level in saved_metadata
            assert saved_metadata[level] is not None

        # Verify auto-tagging was applied
        assert "auto_tags" in saved_metadata
        assert saved_metadata["auto_tags"] == [
            "machine learning",
            "artificial intelligence",
            "python",
            "neural networks",
            "data science",
        ]
        assert "auto_tag_metadata" in saved_metadata
        auto_tag_meta = saved_metadata["auto_tag_metadata"]
        assert auto_tag_meta["source"] == "openai"
        assert auto_tag_meta["tag_count"] == 5

        # Test 2: Version increment on update
        mock_doc_ref.set.reset_mock()
        mock_doc.exists = True
        mock_doc.to_dict = MagicMock(
            return_value={
                "version": 1,
                "lastUpdated": "2025-01-18T09:00:00Z",
                "content": "Original content",
                "author": "Dr. Jane Smith",
                "level_1_category": "research_paper",
            }
        )

        with patch(
            "agent_data_manager.tools.auto_tagging_tool.get_auto_tagging_tool", return_value=mock_auto_tagging_tool
        ):
            updated_metadata = {
                "doc_id": "test_doc_1",
                "content": "Updated content with new machine learning insights",
                "author": "Dr. Jane Smith",
                "category": "research",
            }
            await manager.save_metadata("test_doc_1", updated_metadata)

        # Verify version incremented
        updated_saved = mock_doc_ref.set.call_args[0][0]
        assert updated_saved["version"] == 2
        assert "version_history" in updated_saved
        assert len(updated_saved["version_history"]) == 1
        assert updated_saved["version_history"][0]["version"] == 1

        # Test 3: Change detection logic (non-async)
        manager_sync = FirestoreMetadataManager.__new__(FirestoreMetadataManager)
        old_data = {"content": "Original content", "author": "John Doe", "tags": ["tag1", "tag2"], "version": 1}
        new_data = {
            "content": "Updated content",
            "author": "John Doe",
            "category": "research",
            "tags": ["tag1", "tag3"],
        }
        changes = manager_sync._detect_changes(old_data, new_data)

        # Verify change detection
        assert "modified:content" in changes
        assert "modified:tags" in changes
        assert "added:category" in changes
        assert "modified:author" not in changes  # Author unchanged

        modified_changes = [c for c in changes if c.startswith("modified:")]
        added_changes = [c for c in changes if c.startswith("added:")]
        assert len(modified_changes) == 2  # content and tags
        assert len(added_changes) == 1  # category
