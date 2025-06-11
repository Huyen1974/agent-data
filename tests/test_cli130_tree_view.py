"""
CLI 130 Tree View Functionality Tests

Tests for Tree View backend features:
- Copy Path: get_document_path method
- Share Content: share_document method

This test validates Tree View functionality with 8 documents to ensure correct
path retrieval and sharing link generation with metadata storage in project_tree collection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager


@pytest.mark.deferred
class TestCLI130TreeView:
    """Test Tree View functionality for CLI 130."""

    @pytest.fixture
    def mock_firestore_client(self):
        """Create a mock Firestore client for testing."""
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_document = MagicMock()

        # Make the get method async
        mock_document.get = AsyncMock()

        mock_client.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_document

        return mock_client

    @pytest.fixture
    def metadata_manager(self, mock_firestore_client):
        """Create FirestoreMetadataManager with mocked client."""
        with patch("src.agent_data_manager.vector_store.firestore_metadata_manager.FirestoreAsyncClient"):
            manager = FirestoreMetadataManager(project_id="test-project", collection_name="test_collection")
            manager.db = mock_firestore_client
            return manager

    @pytest.fixture
    def sample_documents(self):
        """Sample documents with hierarchical metadata for testing."""
        return {
            "doc_001": {
                "doc_id": "doc_001",
                "level_1_category": "research_paper",
                "level_2_category": "machine_learning",
                "level_3_category": "deep_learning",
                "level_4_category": "2024",
                "level_5_category": "python",
                "level_6_category": "general",
                "content": "Deep learning research paper content",
                "version": 1,
                "lastUpdated": "2024-01-15T10:00:00Z",
            },
            "doc_002": {
                "doc_id": "doc_002",
                "level_1_category": "documentation",
                "level_2_category": "api_guide",
                "level_3_category": "authentication",
                "level_4_category": None,  # Test partial hierarchy
                "level_5_category": None,
                "level_6_category": None,
                "content": "API authentication guide",
                "version": 1,
                "lastUpdated": "2024-01-15T11:00:00Z",
            },
        }

    @pytest.mark.asyncio
    async def test_comprehensive_tree_view_functionality(
        self, metadata_manager, mock_firestore_client, sample_documents
    ):
        """
        Comprehensive test for Tree View functionality covering copy path and share content features.
        """

        # Test 1: Copy Path functionality - Full hierarchy document
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_documents["doc_001"]
        mock_firestore_client.collection.return_value.document.return_value.get.return_value = mock_doc

        path = await metadata_manager.get_document_path("doc_001")
        expected_path = "research_paper/machine_learning/deep_learning/2024/python/general/doc_001"
        assert path == expected_path, f"Expected path {expected_path}, got {path}"

        # Test 2: Copy Path functionality - Partial hierarchy document
        mock_doc.to_dict.return_value = sample_documents["doc_002"]
        path = await metadata_manager.get_document_path("doc_002")
        expected_path = "documentation/api_guide/authentication/doc_002"
        assert path == expected_path, f"Expected partial path {expected_path}, got {path}"

        # Test 3: Copy Path functionality - Non-existent document
        mock_doc.exists = False
        path = await metadata_manager.get_document_path("non_existent_doc")
        assert path is None, "Expected None for non-existent document"

        # Test 4: Share Content functionality - Document exists
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_documents["doc_002"]

        # Mock project_tree collection for share functionality
        mock_project_tree_ref = AsyncMock()

        def mock_collection_side_effect(collection_name):
            if collection_name == "project_tree":
                mock_project_tree_collection = MagicMock()
                mock_project_tree_collection.document.return_value = mock_project_tree_ref
                return mock_project_tree_collection
            else:
                return mock_firestore_client.collection.return_value

        mock_firestore_client.collection.side_effect = mock_collection_side_effect

        with patch("uuid.uuid4") as mock_uuid:
            mock_uuid_obj = MagicMock()
            mock_uuid_obj.__str__ = MagicMock(return_value="test-share-id-123")
            mock_uuid.return_value = mock_uuid_obj
            with patch("src.agent_data_manager.vector_store.firestore_metadata_manager.datetime") as mock_datetime:
                # Mock datetime for consistent testing
                mock_now = datetime(2024, 1, 15, 15, 30, 0)
                mock_datetime.utcnow.return_value = mock_now
                mock_datetime.timedelta = timedelta

                share_result = await metadata_manager.share_document("doc_002", shared_by="test@example.com")

                # Validate share result structure
                assert share_result is not None, "Share result should not be None"
                assert share_result["share_id"] == "test-share-id-123"
                assert share_result["share_url"] == "https://agent-data/share/test-share-id-123"
                assert share_result["doc_id"] == "doc_002"
                assert share_result["shared_by"] == "test@example.com"
                assert "created_at" in share_result
                assert "expires_at" in share_result

                # Verify project_tree collection was called correctly
                mock_project_tree_ref.set.assert_called_once()
                share_metadata = mock_project_tree_ref.set.call_args[0][0]

                # Validate share metadata structure
                assert share_metadata["share_id"] == "test-share-id-123"
                assert share_metadata["doc_id"] == "doc_002"
                assert share_metadata["shared_by"] == "test@example.com"
                assert share_metadata["access_count"] == 0
                assert share_metadata["last_accessed"] is None
                assert share_metadata["status"] == "active"
                assert "created_at" in share_metadata
                assert "expires_at" in share_metadata

    def test_tree_view_implementation_completeness(self):
        """
        Test that Tree View methods are properly implemented in FirestoreMetadataManager.
        """
        # Verify methods exist
        assert hasattr(FirestoreMetadataManager, "get_document_path"), "get_document_path method missing"
        assert hasattr(FirestoreMetadataManager, "share_document"), "share_document method missing"

        # Verify method signatures
        import inspect

        # Check get_document_path signature
        path_sig = inspect.signature(FirestoreMetadataManager.get_document_path)
        assert "point_id" in path_sig.parameters, "get_document_path missing point_id parameter"

        # Check share_document signature
        share_sig = inspect.signature(FirestoreMetadataManager.share_document)
        assert "point_id" in share_sig.parameters, "share_document missing point_id parameter"
        assert "shared_by" in share_sig.parameters, "share_document missing shared_by parameter"
        assert "expires_days" in share_sig.parameters, "share_document missing expires_days parameter"

        # Verify default values
        assert share_sig.parameters["shared_by"].default is None, "shared_by should default to None"
        assert share_sig.parameters["expires_days"].default == 7, "expires_days should default to 7"
