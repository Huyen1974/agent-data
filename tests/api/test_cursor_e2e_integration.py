"""
End-to-End Cursor Integration Test
Tests the complete workflow from Cursor IDE prompts to Qdrant/Firestore storage
"""

import asyncio
import json
import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool
from agent_data_manager.vector_store.qdrant_store import QdrantStore
from agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager


@pytest.mark.deferred
class TestCursorE2EIntegration:
    """End-to-end integration tests for Cursor IDE to Qdrant/Firestore workflow."""

    @pytest.fixture
    def sample_cursor_documents(self):
        """Sample documents that would come from Cursor IDE prompts."""
        base_time = int(time.time())
        return [
            {
                "doc_id": f"cursor_test_doc_{base_time}_1",
                "content": "How to implement authentication in FastAPI using JWT tokens and OAuth2?",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "how_to",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_2",
                "content": "Best practices for rate limiting in REST APIs to prevent abuse and ensure fair usage",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "best_practices",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_3",
                "content": "How to deploy Docker containers to Google Cloud Run with proper environment variables",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "deployment",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_4",
                "content": "Error handling strategies for asynchronous FastAPI endpoints with proper logging",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "error_handling",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_5",
                "content": "Database connection pooling and transaction management in async Python applications",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "database",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_6",
                "content": "Monitoring and observability setup for microservices using Prometheus and Grafana",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "monitoring",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_7",
                "content": "Security best practices for API endpoints including input validation and sanitization",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "security",
                },
                "tag": "cursor_integration_test",
            },
            {
                "doc_id": f"cursor_test_doc_{base_time}_8",
                "content": "Performance optimization techniques for high-throughput REST APIs with caching strategies",
                "metadata": {
                    "source": "cursor_ide",
                    "user_id": "test_user_001",
                    "project": "api_a2a_gateway",
                    "timestamp": datetime.utcnow().isoformat(),
                    "query_type": "performance",
                },
                "tag": "cursor_integration_test",
            },
        ]

    @pytest.fixture
    def mock_openai_embedding(self):
        """Mock OpenAI embedding response."""
        # Create a realistic 1536-dimensional embedding
        mock_embedding = [0.1] * 1536
        return {
            "embedding": mock_embedding,
            "model": "text-embedding-ada-002",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_single_document_e2e_workflow(self, sample_cursor_documents, mock_openai_embedding):
        """Test end-to-end workflow for a single document from Cursor IDE."""
        doc = sample_cursor_documents[0]

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = mock_openai_embedding["embedding"]
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks with proper async returns using AsyncMock
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": doc["doc_id"]})
                    mock_qdrant_class.return_value = mock_qdrant

                    mock_firestore = AsyncMock()
                    mock_firestore.save_metadata = AsyncMock(return_value=True)
                    mock_firestore_class.return_value = mock_firestore

                    # Setup auto-tagging mock
                    mock_auto_tagging_tool = AsyncMock()
                    mock_auto_tagging_tool.enhance_metadata_with_tags = AsyncMock(return_value=doc["metadata"])
                    mock_auto_tag.return_value = mock_auto_tagging_tool

                    # Initialize vectorization tool with mock embedding provider
                    tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)

                    # Process the document
                    result = await tool.vectorize_document(
                        doc_id=doc["doc_id"],
                        content=doc["content"],
                        metadata=doc["metadata"],
                        tag=doc["tag"],
                        update_firestore=True,
                    )

                    # Verify the result
                    assert result["status"] == "success"
                    assert result["doc_id"] == doc["doc_id"]
                    assert result["embedding_dimension"] == 1536
                    assert result["firestore_updated"] is True

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_batch_document_e2e_workflow(self, sample_cursor_documents, mock_openai_embedding):
        """Test end-to-end workflow for batch processing of Cursor IDE documents."""
        # Take first 4 documents for batch test
        batch_docs = sample_cursor_documents[:4]

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = mock_openai_embedding["embedding"]
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks with proper async returns using AsyncMock
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": "test_id"})
                    mock_qdrant_class.return_value = mock_qdrant

                    mock_firestore = AsyncMock()
                    mock_firestore.save_metadata = AsyncMock(return_value=True)
                    mock_firestore_class.return_value = mock_firestore

                    # Setup auto-tagging mock
                    mock_auto_tagging_tool = AsyncMock()
                    mock_auto_tagging_tool.enhance_metadata_with_tags = AsyncMock(return_value={})
                    mock_auto_tag.return_value = mock_auto_tagging_tool

                    # Initialize vectorization tool with mock embedding provider
                    tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)

                    # Process batch of documents
                    result = await tool.batch_vectorize_documents(
                        documents=batch_docs, tag="cursor_integration_test", update_firestore=True
                    )

                    # Verify batch result
                    assert result["status"] == "completed"
                    assert result["total_documents"] == 4
                    assert result["successful"] == 4
                    assert result["failed"] == 0
                    assert len(result["results"]) == 4

                    # Verify all documents were processed successfully
                    for i, doc_result in enumerate(result["results"]):
                        assert doc_result["status"] == "success"
                        assert doc_result["doc_id"] == batch_docs[i]["doc_id"]
                        assert doc_result["embedding_dimension"] == 1536

                    # Verify QdrantStore was called for each document
                    assert mock_qdrant.upsert_vector.call_count == 4

                    # Verify Firestore was updated for each document (pending + completed for each)
                    assert mock_firestore.save_metadata.call_count >= 8  # 2 calls per document

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_cursor_query_workflow(self, sample_cursor_documents, mock_openai_embedding):
        """Test semantic search workflow that would be triggered from Cursor IDE."""
        query_text = "How to implement authentication in web applications?"

        with patch(
            "agent_data_manager.tools.external_tool_registry.get_openai_embedding", new_callable=AsyncMock
        ) as mock_get_embedding:
            with patch(
                "agent_data_manager.vector_store.qdrant_store.QdrantStore._ensure_collection", new_callable=AsyncMock
            ) as mock_ensure_collection:
                with patch("asyncio.to_thread") as mock_to_thread:
                    with patch("agent_data_manager.vector_store.qdrant_store.QdrantClient") as mock_qdrant_client_class:
                        # Mock _ensure_collection to do nothing
                        mock_ensure_collection.return_value = None

                        # Setup mock search results
                        mock_qdrant_client = AsyncMock()
                        mock_qdrant_client.get_collections.return_value = MagicMock()

                        # Mock asyncio.to_thread to return the search results directly
                        search_results_data = [
                            MagicMock(
                                id=sample_cursor_documents[0]["doc_id"],
                                score=0.95,
                                payload={
                                    "doc_id": sample_cursor_documents[0]["doc_id"],
                                    "content_preview": sample_cursor_documents[0]["content"][:100] + "...",
                                    "source": "cursor_ide",
                                    "query_type": "how_to",
                                },
                            ),
                            MagicMock(
                                id=sample_cursor_documents[6]["doc_id"],
                                score=0.85,
                                payload={
                                    "doc_id": sample_cursor_documents[6]["doc_id"],
                                    "content_preview": sample_cursor_documents[6]["content"][:100] + "...",
                                    "source": "cursor_ide",
                                    "query_type": "security",
                                },
                            ),
                        ]

                        async def mock_to_thread_func(func, *args, **kwargs):
                            # Return the search results directly when called for search
                            if hasattr(func, "__name__") and "search" in str(func):
                                return search_results_data
                            return func(*args, **kwargs)

                        mock_to_thread.side_effect = mock_to_thread_func

                        mock_qdrant_client_class.return_value = mock_qdrant_client

                        # Setup embedding mock - make it properly async
                        async def mock_embedding_func(*args, **kwargs):
                            return mock_openai_embedding

                        mock_get_embedding.side_effect = mock_embedding_func

                        # Initialize QdrantStore
                        qdrant_store = QdrantStore(
                            url="https://mock-qdrant.example.com",
                            api_key="mock_key",
                            collection_name="test_collection",
                            vector_size=1536,
                        )

                        # Perform semantic search
                        search_results = await qdrant_store.semantic_search(
                            query_text=query_text, limit=5, tag="cursor_integration_test", score_threshold=0.7
                        )

                        # Verify search results
                        assert "results" in search_results
                        assert len(search_results["results"]) == 2
                        assert search_results["results"][0]["score"] == 0.95
                        assert search_results["results"][1]["score"] == 0.85

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_cursor_metadata_validation_workflow(self, sample_cursor_documents):
        """Test metadata validation and enhancement during Cursor IDE workflow."""
        doc = sample_cursor_documents[0]

        # Test with enhanced metadata that includes auto-tagging results
        enhanced_metadata = {
            **doc["metadata"],
            "auto_tags": ["authentication", "jwt", "fastapi", "oauth2"],
            "confidence_scores": [0.95, 0.88, 0.92, 0.85],
            "content_hash": "sha256_mock_hash",
            "version": "1.0",
        }

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = [0.1] * 1536
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks with proper async returns using AsyncMock
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": doc["doc_id"]})
                    mock_qdrant_class.return_value = mock_qdrant

                    mock_firestore = AsyncMock()
                    mock_firestore.save_metadata = AsyncMock(return_value=True)
                    mock_firestore_class.return_value = mock_firestore

                    # Setup auto-tagging mock
                    mock_auto_tagging_tool = AsyncMock()
                    mock_auto_tagging_tool.enhance_metadata_with_tags = AsyncMock(return_value=enhanced_metadata)
                    mock_auto_tag.return_value = mock_auto_tagging_tool

                    # Initialize vectorization tool with mock embedding provider
                    tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)

                    # Process document with enhanced metadata
                    result = await tool.vectorize_document(
                        doc_id=doc["doc_id"],
                        content=doc["content"],
                        metadata=enhanced_metadata,
                        tag=doc["tag"],
                        update_firestore=True,
                    )

                    # Verify successful processing
                    assert result["status"] == "success"
                    assert result["doc_id"] == doc["doc_id"]
                    assert result["firestore_updated"] is True

    @pytest.mark.asyncio
    @pytest.mark.deferred
    async def test_cursor_integration_data_consistency(self, sample_cursor_documents):
        """Test data consistency between Qdrant and Firestore in Cursor workflow."""
        doc = sample_cursor_documents[0]

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = [0.1] * 1536
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks to track calls with proper async returns using AsyncMock
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_vector = AsyncMock(return_value={"success": True, "vector_id": doc["doc_id"]})
                    mock_qdrant_class.return_value = mock_qdrant

                    mock_firestore = AsyncMock()
                    mock_firestore.save_metadata = AsyncMock(return_value=True)
                    mock_firestore_class.return_value = mock_firestore

                    # Setup auto-tagging mock
                    mock_auto_tagging_tool = AsyncMock()
                    mock_auto_tagging_tool.enhance_metadata_with_tags = AsyncMock(return_value=doc["metadata"])
                    mock_auto_tag.return_value = mock_auto_tagging_tool

                    # Initialize vectorization tool with mock embedding provider
                    tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)

                    # Process document
                    result = await tool.vectorize_document(
                        doc_id=doc["doc_id"],
                        content=doc["content"],
                        metadata=doc["metadata"],
                        tag=doc["tag"],
                        update_firestore=True,
                    )

                    # Verify successful processing
                    assert result["status"] == "success"
                    assert result["doc_id"] == doc["doc_id"]
                    assert result["firestore_updated"] is True

                    # Verify data consistency
                    mock_qdrant.upsert_vector.assert_called_once()
                    assert mock_firestore.save_metadata.call_count >= 2
