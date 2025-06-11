"""Test QdrantVectorizationTool with Firestore sync functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.call_count = 0

    async def embed_single(self, text: str):
        """Generate mock embedding for a single text."""
        self.call_count += 1
        if self.should_fail:
            from agent_data_manager.embedding.embedding_provider import EmbeddingError

            raise EmbeddingError("Mock embedding failure", status_code=500, provider="mock")
        return [0.1] * 1536

    def get_model_name(self) -> str:
        return "test-embedding-model"


@pytest.fixture
def mock_tool_dependencies():
    """Mock all dependencies for QdrantVectorizationTool."""
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.get_qdrant_config.return_value = {
        "url": "https://mock-qdrant.example.com",
        "api_key": "mock-api-key",
        "collection_name": "test_collection",
        "vector_size": 1536,
    }
    mock_settings.get_firestore_config.return_value = {
        "project_id": "test-project",
        "metadata_collection": "test_metadata",
    }

    # Mock QdrantStore
    mock_qdrant_store = AsyncMock()
    mock_qdrant_store.upsert_vector.return_value = {"success": True, "vector_id": "test_vector_id"}

    # Mock FirestoreMetadataManager
    mock_firestore_manager = AsyncMock()
    mock_firestore_manager.save_metadata.return_value = True

    # Mock auto-tagging tool
    mock_auto_tagging_tool = AsyncMock()
    mock_auto_tagging_tool.enhance_metadata_with_tags.return_value = {"enhanced": True}

    # Create mock embedding provider
    mock_embedding_provider = MockEmbeddingProvider()

    with patch("agent_data_manager.tools.qdrant_vectorization_tool.settings", mock_settings), patch(
        "agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore", return_value=mock_qdrant_store
    ), patch(
        "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager",
        return_value=mock_firestore_manager,
    ), patch(
        "agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool", return_value=mock_auto_tagging_tool
    ):

        yield {
            "settings": mock_settings,
            "qdrant_store": mock_qdrant_store,
            "firestore_manager": mock_firestore_manager,
            "auto_tagging_tool": mock_auto_tagging_tool,
            "embedding_provider": mock_embedding_provider,
        }


@pytest.mark.asyncio
async def test_firestore_sync_pending_to_completed(mock_tool_dependencies):
    """Test that vectorStatus is updated from pending to completed in Firestore."""
    # Import after mocking
    from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

    tool = QdrantVectorizationTool(embedding_provider=mock_tool_dependencies["embedding_provider"])

    # Test document vectorization with Firestore sync
    result = await tool.vectorize_document(
        doc_id="test_doc_1",
        content="Test document content for vectorization",
        metadata={"source": "test"},
        tag="test_tag",
        update_firestore=True,
    )

    # Verify vectorization succeeded
    assert result["status"] == "success"
    assert result["doc_id"] == "test_doc_1"
    assert result["firestore_updated"] is True

    # Verify Firestore was called to update status
    firestore_manager = mock_tool_dependencies["firestore_manager"]
    assert firestore_manager.save_metadata.call_count >= 2  # pending + completed calls


@pytest.mark.asyncio
async def test_firestore_sync_failure_status(mock_tool_dependencies):
    """Test that vectorStatus is set to failed when vectorization fails."""
    # Create a failing embedding provider
    failing_provider = MockEmbeddingProvider(should_fail=True)

    # Import after mocking
    from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

    tool = QdrantVectorizationTool(embedding_provider=failing_provider)

    # Test document vectorization failure
    result = await tool.vectorize_document(
        doc_id="test_doc_fail",
        content="Test document that will fail",
        metadata={"source": "test"},
        update_firestore=True,
    )

    # Verify vectorization failed
    assert result["status"] == "failed"
    assert result["doc_id"] == "test_doc_fail"

    # Verify Firestore was called to update status
    firestore_manager = mock_tool_dependencies["firestore_manager"]
    assert firestore_manager.save_metadata.call_count >= 1  # At least pending call


@pytest.mark.asyncio
async def test_batch_vectorization_firestore_sync(mock_tool_dependencies):
    """Test batch vectorization with Firestore sync for multiple documents."""
    # Import after mocking
    from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

    tool = QdrantVectorizationTool(embedding_provider=mock_tool_dependencies["embedding_provider"])

    # Test batch vectorization
    documents = [
        {"doc_id": "batch_doc_1", "content": "First batch document", "metadata": {"batch": 1}},
        {"doc_id": "batch_doc_2", "content": "Second batch document", "metadata": {"batch": 1}},
        {"doc_id": "batch_doc_3", "content": "Third batch document", "metadata": {"batch": 1}},
    ]

    result = await tool.batch_vectorize_documents(documents=documents, tag="batch_test", update_firestore=True)

    # Verify batch operation succeeded
    assert result["status"] == "completed"
    assert result["total_documents"] == 3
    assert result["successful"] == 3
    assert result["failed"] == 0

    # Verify Firestore was called for each document
    firestore_manager = mock_tool_dependencies["firestore_manager"]
    assert firestore_manager.save_metadata.call_count >= 3  # At least one call per document


@pytest.mark.asyncio
async def test_vectorization_without_firestore_sync(mock_tool_dependencies):
    """Test vectorization with Firestore sync disabled."""
    # Import after mocking
    from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool

    tool = QdrantVectorizationTool(embedding_provider=mock_tool_dependencies["embedding_provider"])

    # Test document vectorization without Firestore sync
    result = await tool.vectorize_document(
        doc_id="test_doc_no_sync", content="Test document without Firestore sync", update_firestore=False
    )

    # Verify vectorization succeeded
    assert result["status"] == "success"
    assert result["doc_id"] == "test_doc_no_sync"
    assert result["firestore_updated"] is False

    # Verify Firestore was not called
    firestore_manager = mock_tool_dependencies["firestore_manager"]
    assert firestore_manager.save_metadata.call_count == 0
