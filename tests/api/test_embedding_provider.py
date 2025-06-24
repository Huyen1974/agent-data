"""Test embedding provider abstraction in Agent Data system."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool


class MockEmbeddingProvider:
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 1536, model_name: str = "test-model"):
        self.dimension = dimension
        self.model_name = model_name
        self.call_count = 0

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for a list of texts."""
        self.call_count += len(texts)
        return [[0.1] * self.dimension for _ in texts]

    async def embed_single(self, text: str) -> List[float]:
        """Generate mock embedding for a single text."""
        self.call_count += 1
        return [0.1] * self.dimension

    def get_embedding_dimension(self) -> int:
        """Get the dimension size."""
        return self.dimension

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name


@pytest.mark.asyncio
class TestEmbeddingProviderInterface:
    """Test the embedding provider interface and abstraction."""

    async def test_mock_embedding_provider_basic_functionality(self):
        """Test that mock embedding provider works correctly."""
        provider = MockEmbeddingProvider(dimension=512, model_name="test-mock")

        # Test single embedding
        embedding = await provider.embed_single("test text")
        assert len(embedding) == 512
        assert all(x == 0.1 for x in embedding)
        assert provider.call_count == 1

        # Test batch embedding
        embeddings = await provider.embed(["text1", "text2", "text3"])
        assert len(embeddings) == 3
        assert all(len(emb) == 512 for emb in embeddings)
        assert provider.call_count == 4  # 1 + 3

        # Test metadata
        assert provider.get_embedding_dimension() == 512
        assert provider.get_model_name() == "test-mock"

    @patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore")
    @patch("agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager")
    async def test_vectorization_tool_uses_custom_embedding_provider(self, mock_firestore, mock_qdrant):
        """Test that QdrantVectorizationTool uses the provided embedding provider."""
        # Setup mocks
        mock_qdrant_instance = Mock()
        mock_qdrant_instance.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": "test_doc"})
        mock_qdrant.return_value = mock_qdrant_instance

        mock_firestore_instance = Mock()
        mock_firestore_instance.save_metadata = AsyncMock()
        mock_firestore.return_value = mock_firestore_instance

        # Create tool with custom embedding provider
        embedding_provider = MockEmbeddingProvider(dimension=768, model_name="custom-test-model")
        tool = QdrantVectorizationTool(embedding_provider=embedding_provider)

        # Mock settings
        with patch("agent_data_manager.tools.qdrant_vectorization_tool.settings") as mock_settings:
            mock_settings.get_qdrant_config.return_value = {
                "url": "test_url",
                "api_key": "test_key",
                "collection_name": "test_collection",
                "vector_size": 768,
            }
            mock_settings.get_firestore_config.return_value = {
                "project_id": "test_project",
                "metadata_collection": "test_metadata",
            }

            # Test vectorization
            result = await tool.vectorize_document(
                doc_id="test_doc",
                content="test content",
                metadata={"test": "data"},
                update_firestore=False,
                enable_auto_tagging=False,
            )

        # Verify result
        assert result["status"] == "success"
        assert result["doc_id"] == "test_doc"
        assert result["embedding_dimension"] == 768
        assert embedding_provider.call_count == 1

        # Verify the embedding provider was used
        assert mock_qdrant_instance.upsert_vector.called
        call_args = mock_qdrant_instance.upsert_vector.call_args
        assert call_args[1]["vector"] == [0.1] * 768

        # Verify metadata includes custom model name
        metadata_arg = call_args[1]["metadata"]
        assert metadata_arg["embedding_model"] == "custom-test-model"
