"""
Test cases for metadata versioning, auto-tagging, and hierarchical structure functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest

from agent_data_manager.tools.auto_tagging_tool import (
    AutoTaggingTool,
    get_auto_tagging_tool,
)
from agent_data_manager.vector_store.firestore_metadata_manager import (
    FirestoreMetadataManager,
)


class TestMetadataVersioning:
    """Test metadata versioning functionality."""

    @pytest.fixture
    def mock_firestore_client(self):
        """Mock Firestore client."""
        mock_client = AsyncMock()
        mock_doc_ref = AsyncMock()
        mock_collection = AsyncMock()

        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref

        return mock_client, mock_doc_ref

    @pytest.fixture
    def metadata_manager(self, mock_firestore_client):
        """Create FirestoreMetadataManager with mocked client."""
        mock_client, mock_doc_ref = mock_firestore_client

        with patch(
            "agent_data_manager.vector_store.firestore_metadata_manager.FirestoreAsyncClient"
        ) as mock_firestore:
            mock_firestore.return_value = mock_client
            manager = FirestoreMetadataManager(
                project_id="test-project", collection_name="test_metadata"
            )
            # Override the db attribute directly
            manager.db = mock_client
            return manager, mock_doc_ref

    def test_metadata_versioning_logic(self):
        """Test versioning logic without async complexity."""
        manager = FirestoreMetadataManager.__new__(FirestoreMetadataManager)

        # Test change detection
        old_data = {"content": "old", "author": "old_author"}
        new_data = {"content": "new", "author": "old_author", "title": "new_title"}

        changes = manager._detect_changes(old_data, new_data)

        assert "modified:content" in changes
        assert "added:title" in changes
        assert "modified:author" not in changes

    def test_hierarchical_structure_logic(self):
        """Test hierarchical structure logic without async complexity."""
        manager = FirestoreMetadataManager.__new__(FirestoreMetadataManager)

        # Test metadata with fields that should populate hierarchy
        test_metadata = {
            "doc_id": "test_doc_1",
            "doc_type": "research_paper",
            "tag": "machine_learning",
            "author": "John Doe",
            "year": 2025,
            "language": "english",
            "format": "pdf",
        }

        enhanced_metadata = manager._ensure_hierarchical_structure(test_metadata)

        # Verify hierarchical structure
        assert enhanced_metadata["level_1_category"] == "research_paper"
        assert enhanced_metadata["level_2_category"] == "machine_learning"
        assert enhanced_metadata["level_3_category"] == "John Doe"
        assert enhanced_metadata["level_4_category"] == "2025"
        assert enhanced_metadata["level_5_category"] == "english"
        assert enhanced_metadata["level_6_category"] == "pdf"


class TestAutoTagging:
    """Test auto-tagging functionality."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client."""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_choice = AsyncMock()
        mock_message = AsyncMock()
        mock_usage = AsyncMock()

        mock_message.content = "machine learning, artificial intelligence, neural networks, deep learning, python"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 20
        mock_usage.total_tokens = 120
        mock_response.usage = mock_usage

        mock_client.chat.completions.create.return_value = mock_response

        return mock_client

    @pytest.fixture
    def auto_tagging_tool(self, mock_openai_client):
        """Create AutoTaggingTool with mocked dependencies."""
        with (
            patch(
                "agent_data_manager.tools.auto_tagging_tool.openai_client",
                mock_openai_client,
            ),
            patch("agent_data_manager.tools.auto_tagging_tool.OPENAI_AVAILABLE", True),
            patch(
                "agent_data_manager.tools.auto_tagging_tool.settings"
            ) as mock_settings,
        ):

            mock_settings.get_firestore_config.return_value = {
                "project_id": "test-project"
            }

            tool = AutoTaggingTool()
            tool._initialized = True  # Skip initialization
            return tool

    def test_content_hash_generation(self):
        """Test content hash generation."""
        tool = AutoTaggingTool()

        content1 = "This is test content"
        content2 = "This is different content"
        content3 = "This is test content"  # Same as content1

        hash1 = tool._generate_content_hash(content1)
        hash2 = tool._generate_content_hash(content2)
        hash3 = tool._generate_content_hash(content3)

        assert hash1 != hash2  # Different content should have different hashes
        assert hash1 == hash3  # Same content should have same hash
        assert len(hash1) == 64  # SHA256 hash should be 64 characters

    def test_get_auto_tagging_tool_singleton(self):
        """Test that get_auto_tagging_tool returns singleton instance."""
        tool1 = get_auto_tagging_tool()
        tool2 = get_auto_tagging_tool()

        assert tool1 is tool2
        assert isinstance(tool1, AutoTaggingTool)
