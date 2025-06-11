"""
CLI 132 Test: CS Agent API Layer

Tests the FastAPI endpoints for Tree View and Search functionality:
- /tree-view/{doc_id} endpoint for copy path and share content
- /search endpoint for advanced search (path, tags, metadata)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import json

# Import the FastAPI app
from src.agent_data_manager.cs_agent_api import app, get_firestore_manager


@pytest.mark.deferred
class TestCLI132CSAgentAPI:
    """Test CS Agent API endpoints for Tree View and Search functionality."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_firestore_manager(self):
        """Create mock FirestoreMetadataManager with test data."""
        mock_manager = AsyncMock()

        # Mock document path responses
        mock_manager.get_document_path.return_value = "research_paper/machine_learning/doc_001"

        # Mock share document responses
        mock_manager.share_document.return_value = {
            "share_id": "test-share-id-123",
            "share_url": "https://agent-data/share/test-share-id-123",
            "doc_id": "doc_001",
            "created_at": "2024-01-01T00:00:00",
            "expires_at": "2024-01-08T00:00:00",
            "shared_by": "test@example.com",
        }

        # Mock metadata responses
        mock_manager.get_metadata_with_version.return_value = {
            "title": "Test Document",
            "author": "John Doe",
            "year": 2024,
            "auto_tags": ["python", "machine_learning"],
            "level_1_category": "research_paper",
            "level_2_category": "machine_learning",
        }

        # Mock search responses
        mock_manager.search_by_path.return_value = [
            {
                "_doc_id": "doc_001",
                "title": "ML Research Paper",
                "level_1_category": "research_paper",
                "_matched_level": "level_1_category",
            },
            {
                "_doc_id": "doc_002",
                "title": "AI Research Paper",
                "level_1_category": "research_paper",
                "_matched_level": "level_1_category",
            },
        ]

        mock_manager.search_by_tags.return_value = [
            {
                "_doc_id": "doc_003",
                "title": "Python Tutorial",
                "auto_tags": ["python", "tutorial"],
                "_matched_tags": ["python"],
            },
            {
                "_doc_id": "doc_004",
                "title": "Python Guide",
                "auto_tags": ["python", "guide"],
                "_matched_tags": ["python"],
            },
        ]

        mock_manager.search_by_metadata.return_value = [
            {
                "_doc_id": "doc_005",
                "title": "John's 2024 Paper",
                "author": "John Doe",
                "year": 2024,
                "_matched_filters": {"author": "John Doe", "year": 2024},
            },
            {
                "_doc_id": "doc_006",
                "title": "John's 2024 Report",
                "author": "John Doe",
                "year": 2024,
                "_matched_filters": {"author": "John Doe", "year": 2024},
            },
        ]

        return mock_manager

    def test_tree_view_endpoint_success(self, client, mock_firestore_manager):
        """Test /tree-view endpoint returns correct path and share data."""
        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/tree-view/doc_001?shared_by=test@example.com&expires_days=7")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["status"] == "ok"
            assert data["path"] == "research_paper/machine_learning/doc_001"
            assert data["share_url"] == "https://agent-data/share/test-share-id-123"
            assert "metadata" in data
            assert data["metadata"]["title"] == "Test Document"
            assert data["metadata"]["author"] == "John Doe"

            # Verify mock calls
            mock_firestore_manager.get_document_path.assert_called_once_with("doc_001")
            mock_firestore_manager.share_document.assert_called_once_with(
                "doc_001", shared_by="test@example.com", expires_days=7
            )
            mock_firestore_manager.get_metadata_with_version.assert_called_once_with("doc_001")

    def test_tree_view_endpoint_not_found(self, client, mock_firestore_manager):
        """Test /tree-view endpoint handles document not found."""
        # Mock all methods to return None (document not found)
        mock_firestore_manager.get_document_path.return_value = None
        mock_firestore_manager.share_document.return_value = None
        mock_firestore_manager.get_metadata_with_version.return_value = None

        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/tree-view/nonexistent_doc")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def test_search_endpoint_by_path(self, client, mock_firestore_manager):
        """Test /search endpoint with path parameter."""
        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/search?path=research_paper")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["status"] == "ok"
            assert data["total"] == 2
            assert len(data["results"]) == 2

            # Verify search results
            assert data["results"][0]["_doc_id"] == "doc_001"
            assert data["results"][0]["title"] == "ML Research Paper"
            assert data["results"][1]["_doc_id"] == "doc_002"
            assert data["results"][1]["title"] == "AI Research Paper"

            # Verify mock call
            mock_firestore_manager.search_by_path.assert_called_once_with("research_paper")

    def test_search_endpoint_by_tags(self, client, mock_firestore_manager):
        """Test /search endpoint with tags parameter."""
        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/search?tags=python,tutorial")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["status"] == "ok"
            assert data["total"] == 2
            assert len(data["results"]) == 2

            # Verify search results
            assert data["results"][0]["_doc_id"] == "doc_003"
            assert data["results"][0]["title"] == "Python Tutorial"
            assert data["results"][1]["_doc_id"] == "doc_004"
            assert data["results"][1]["title"] == "Python Guide"

            # Verify mock call
            mock_firestore_manager.search_by_tags.assert_called_once_with(["python", "tutorial"])

    def test_search_endpoint_by_metadata(self, client, mock_firestore_manager):
        """Test /search endpoint with metadata parameter."""
        metadata_json = json.dumps({"author": "John Doe", "year": 2024})

        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get(f"/search?metadata={metadata_json}")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["status"] == "ok"
            assert data["total"] == 2
            assert len(data["results"]) == 2

            # Verify search results
            assert data["results"][0]["_doc_id"] == "doc_005"
            assert data["results"][0]["title"] == "John's 2024 Paper"
            assert data["results"][1]["_doc_id"] == "doc_006"
            assert data["results"][1]["title"] == "John's 2024 Report"

            # Verify mock call
            mock_firestore_manager.search_by_metadata.assert_called_once_with({"author": "John Doe", "year": 2024})

    def test_search_endpoint_combined_parameters(self, client, mock_firestore_manager):
        """Test /search endpoint with multiple parameters (deduplication)."""
        # Set up overlapping results to test deduplication
        mock_firestore_manager.search_by_path.return_value = [{"_doc_id": "doc_001", "title": "Shared Document"}]
        mock_firestore_manager.search_by_tags.return_value = [
            {"_doc_id": "doc_001", "title": "Shared Document"},  # Duplicate
            {"_doc_id": "doc_002", "title": "Unique Document"},
        ]

        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/search?path=research&tags=python")

            assert response.status_code == 200
            data = response.json()

            # Verify deduplication worked
            assert data["status"] == "ok"
            assert data["total"] == 2  # Should be 2, not 3 (duplicate removed)

            doc_ids = [result["_doc_id"] for result in data["results"]]
            assert "doc_001" in doc_ids
            assert "doc_002" in doc_ids
            assert len(set(doc_ids)) == 2  # No duplicates

    def test_search_endpoint_invalid_metadata_json(self, client, mock_firestore_manager):
        """Test /search endpoint with invalid JSON metadata."""
        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/search?metadata=invalid-json")

            assert response.status_code == 400
            assert "Invalid JSON format" in response.json()["detail"]

    def test_search_endpoint_no_parameters(self, client, mock_firestore_manager):
        """Test /search endpoint with no parameters returns empty results."""
        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/search")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "ok"
            assert data["total"] == 0
            assert data["results"] == []

    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "CS Agent API"

    def test_api_error_handling(self, client, mock_firestore_manager):
        """Test API error handling for internal server errors."""
        # Mock an exception in the firestore manager
        mock_firestore_manager.get_document_path.side_effect = Exception("Database error")

        with patch.object(app, "dependency_overrides", {get_firestore_manager: lambda: mock_firestore_manager}):
            response = client.get("/tree-view/doc_001")

            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
