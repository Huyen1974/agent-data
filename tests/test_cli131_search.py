"""
CLI 131 Test Suite - Advanced Search Functionality for Tree View

This module tests the advanced search functionality implemented in CLI 131:
- Search by path (hierarchical path segments)
- Search by tags (auto_tags field)
- Search by metadata (flexible field filtering)

Test Strategy:
- Use mocked Firestore for fast execution (<1 second)
- Test all search methods with various scenarios
- Validate search accuracy and error handling
- Ensure integration with existing Tree View functionality

Author: CLI 131 Implementation
Date: 2024-01-15
"""

import pytest
from unittest.mock import MagicMock

from src.agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager


@pytest.mark.deferred
class TestCLI131AdvancedSearch:
    """Test suite for CLI 131 advanced search functionality."""

    @pytest.fixture
    def mock_firestore_manager(self):
        """Create a mocked FirestoreMetadataManager for testing."""
        manager = FirestoreMetadataManager()
        manager.db = MagicMock()
        return manager

    @pytest.fixture
    def sample_documents(self):
        """Sample documents for search testing."""
        return [
            {
                "_doc_id": "doc_001",
                "level_1_category": "research_paper",
                "level_2_category": "machine_learning",
                "level_3_category": "deep_learning",
                "auto_tags": ["python", "tensorflow", "neural_networks"],
                "author": "John Doe",
                "year": 2024,
                "vectorStatus": "completed",
            },
            {
                "_doc_id": "doc_002",
                "level_1_category": "documentation",
                "level_2_category": "api_guide",
                "level_3_category": "authentication",
                "auto_tags": ["api", "security", "oauth"],
                "author": "Jane Smith",
                "year": 2023,
                "vectorStatus": "pending",
            },
            {
                "_doc_id": "doc_003",
                "level_1_category": "research_paper",
                "level_2_category": "data_science",
                "level_3_category": "statistics",
                "auto_tags": ["python", "pandas", "statistics"],
                "author": "John Doe",
                "year": 2024,
                "vectorStatus": "completed",
            },
        ]

    @pytest.mark.asyncio
    async def test_comprehensive_advanced_search_functionality(self, mock_firestore_manager, sample_documents):
        """
        Comprehensive test for all advanced search functionality in CLI 131.

        Tests:
        1. Search by Path - hierarchical path matching
        2. Search by Tags - tag-based filtering
        3. Search by Metadata - flexible field filtering
        4. Error handling - database not initialized
        5. Edge cases - empty queries, no results
        """

        # Test 1: Search by Path - Research Papers
        mock_query = MagicMock()

        # Mock documents for path search "research_paper"
        research_docs = [doc for doc in sample_documents if doc.get("level_1_category") == "research_paper"]
        mock_docs = []
        for doc in research_docs:
            mock_doc = MagicMock()
            mock_doc.id = doc["_doc_id"]
            mock_doc.to_dict.return_value = doc
            mock_docs.append(mock_doc)

        def mock_stream():
            return iter(mock_docs)

        mock_query.stream = mock_stream
        mock_firestore_manager.db.collection.return_value.where.return_value.where.return_value = mock_query

        # Execute search by path
        path_results = await mock_firestore_manager.search_by_path("research_paper")

        # Validate path search results
        assert len(path_results) == 2, f"Expected 2 research papers, got {len(path_results)}"
        assert all(
            "research_paper" in doc.get("level_1_category", "") for doc in path_results
        ), "All results should contain 'research_paper' in path"
        assert all("_matched_level" in doc for doc in path_results), "All results should have matched level information"

        # Test 2: Search by Tags - Python Documents
        mock_query_tags = MagicMock()

        # Mock documents for tag search "python"
        python_docs = [doc for doc in sample_documents if "python" in doc.get("auto_tags", [])]
        mock_docs_tags = []
        for doc in python_docs:
            mock_doc = MagicMock()
            mock_doc.id = doc["_doc_id"]
            mock_doc.to_dict.return_value = doc
            mock_docs_tags.append(mock_doc)

        def mock_stream_tags():
            return iter(mock_docs_tags)

        mock_query_tags.stream = mock_stream_tags
        mock_firestore_manager.db.collection.return_value.where.return_value = mock_query_tags

        # Execute search by tags
        tag_results = await mock_firestore_manager.search_by_tags(["python"])

        # Validate tag search results
        assert len(tag_results) == 2, f"Expected 2 Python documents, got {len(tag_results)}"
        assert all(
            "python" in doc.get("auto_tags", []) for doc in tag_results
        ), "All results should contain 'python' tag"
        assert all("_matched_tags" in doc for doc in tag_results), "All results should have matched tags information"

        # Test 3: Search by Metadata - John Doe's 2024 Documents
        mock_query_metadata = MagicMock()

        # Mock documents for metadata search
        john_2024_docs = [
            doc for doc in sample_documents if doc.get("author") == "John Doe" and doc.get("year") == 2024
        ]
        mock_docs_metadata = []
        for doc in john_2024_docs:
            mock_doc = MagicMock()
            mock_doc.id = doc["_doc_id"]
            mock_doc.to_dict.return_value = doc
            mock_docs_metadata.append(mock_doc)

        def mock_stream_metadata():
            return iter(mock_docs_metadata)

        mock_query_metadata.stream = mock_stream_metadata

        # Chain where clauses for multiple filters
        mock_query_chain = MagicMock()
        mock_query_chain.where.return_value = mock_query_metadata
        mock_firestore_manager.db.collection.return_value.where.return_value = mock_query_chain

        # Execute search by metadata
        metadata_results = await mock_firestore_manager.search_by_metadata({"author": "John Doe", "year": 2024})

        # Validate metadata search results
        assert len(metadata_results) == 2, f"Expected 2 John Doe 2024 documents, got {len(metadata_results)}"
        assert all(
            doc.get("author") == "John Doe" for doc in metadata_results
        ), "All results should be authored by John Doe"
        assert all(doc.get("year") == 2024 for doc in metadata_results), "All results should be from 2024"
        assert all(
            "_matched_filters" in doc for doc in metadata_results
        ), "All results should have matched filters information"

        # Test 4: Error Handling - Database Not Initialized
        manager_no_db = FirestoreMetadataManager()
        manager_no_db.db = None

        path_error_results = await manager_no_db.search_by_path("test")
        tags_error_results = await manager_no_db.search_by_tags(["test"])
        metadata_error_results = await manager_no_db.search_by_metadata({"test": "value"})

        assert path_error_results == [], "Should return empty list when database not initialized"
        assert tags_error_results == [], "Should return empty list when database not initialized"
        assert metadata_error_results == [], "Should return empty list when database not initialized"

        # Test 5: Edge Cases - Empty Queries
        empty_path_results = await mock_firestore_manager.search_by_path("")
        empty_tags_results = await mock_firestore_manager.search_by_tags([])
        empty_metadata_results = await mock_firestore_manager.search_by_metadata({})

        assert empty_path_results == [], "Should return empty list for empty path query"
        assert empty_tags_results == [], "Should return empty list for empty tags"
        assert empty_metadata_results == [], "Should return empty list for empty metadata filters"

        print("✅ CLI 131 Advanced Search Functionality Test Passed")
        print(f"   - Path Search: Found {len(path_results)} research papers")
        print(f"   - Tag Search: Found {len(tag_results)} Python documents")
        print(f"   - Metadata Search: Found {len(metadata_results)} John Doe 2024 documents")
        print("   - Error handling and edge cases validated")


if __name__ == "__main__":
    # Run the test directly for development
    pytest.main([__file__, "-v"])
