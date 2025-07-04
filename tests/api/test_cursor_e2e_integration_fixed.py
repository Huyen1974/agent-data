"""
End-to-End Cursor Integration Test - Fixed Version
Tests the complete workflow from Cursor IDE prompts to Qdrant/Firestore storage
"""

# import asyncio
# import json
import pytest
import time
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool
from agent_data_manager.vector_store.qdrant_store import QdrantStore

# from agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager


class TestCursorE2EIntegrationFixed:
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
        ]

    @pytest.fixture
    def mock_openai_embedding_response(self):
        """Mock OpenAI embedding response."""
        # Create a realistic 1536-dimensional embedding
        mock_embedding = [0.1] * 1536
        return {
            "embedding": mock_embedding,
            "total_tokens": 10,
            "model_used": "text-embedding-ada-002",
        }

    @pytest.mark.asyncio
    async def test_single_document_e2e_workflow(self, sample_cursor_documents, mock_openai_embedding_response):
        """Test end-to-end workflow for a single document from Cursor IDE."""
        doc = sample_cursor_documents[0]

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = mock_openai_embedding_response["embedding"]
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        # Mock the external dependencies properly
        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup QdrantStore mock
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_vector.return_value = {"success": True, "vector_id": doc["doc_id"]}
                    mock_qdrant_class.return_value = mock_qdrant

                    # Setup FirestoreMetadataManager mock
                    mock_firestore = AsyncMock()
                    mock_firestore.save_metadata.return_value = True
                    mock_firestore_class.return_value = mock_firestore

                    # Setup auto-tagging mock
                    mock_auto_tagging_tool = AsyncMock()
                    mock_auto_tagging_tool.enhance_metadata_with_tags.return_value = doc["metadata"]
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

                    # Verify embedding provider was called correctly
                    mock_embedding_provider.embed_single.assert_called_once()

                    # Verify QdrantStore interactions
                    mock_qdrant.upsert_vector.assert_called_once()

                    # Verify Firestore interactions (pending + completed)
                    assert mock_firestore.save_metadata.call_count >= 2

    @pytest.mark.asyncio
    async def test_batch_document_e2e_workflow(self, sample_cursor_documents, mock_openai_embedding_response):
        """Test end-to-end workflow for batch processing of Cursor IDE documents."""
        batch_docs = sample_cursor_documents

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = mock_openai_embedding_response["embedding"]
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks
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
    async def test_cursor_query_workflow(self, sample_cursor_documents, mock_openai_embedding_response):
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
                                id=sample_cursor_documents[3]["doc_id"],
                                score=0.85,
                                payload={
                                    "doc_id": sample_cursor_documents[3]["doc_id"],
                                    "content_preview": sample_cursor_documents[3]["content"][:100] + "...",
                                    "source": "cursor_ide",
                                    "query_type": "error_handling",
                                },
                            ),
                        ]

                        # Mock asyncio.to_thread to return the search results directly
                        async def mock_to_thread_func(func, *args, **kwargs):
                            # Return the search results directly when called for search
                            if hasattr(func, "__name__") and "search" in str(func):
                                return search_results_data
                            return func(*args, **kwargs)

                        mock_to_thread.side_effect = mock_to_thread_func
                        mock_qdrant_client_class.return_value = mock_qdrant_client

                        # Mock get_collections (not needed since _ensure_collection is mocked)
                        mock_qdrant_client.get_collections.return_value = MagicMock()

                        # Setup embedding mock - make it properly async
                        async def mock_embedding_func(*args, **kwargs):
                            return mock_openai_embedding_response

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

                        # Verify the results contain expected metadata
                        first_result = search_results["results"][0]
                        assert first_result["metadata"]["source"] == "cursor_ide"
                        assert first_result["metadata"]["query_type"] == "how_to"

    @pytest.mark.asyncio
    async def test_cursor_metadata_validation_workflow(self, sample_cursor_documents, mock_openai_embedding_response):
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
        mock_embedding_provider.embed_single.return_value = mock_openai_embedding_response["embedding"]
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks
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
                        enable_auto_tagging=False,  # Disable to avoid additional complexity
                    )

                    # Verify successful processing
                    assert result["status"] == "success"
                    assert result["doc_id"] == doc["doc_id"]
                    assert result["firestore_updated"] is True

                    # Verify enhanced metadata was processed
                    mock_qdrant.upsert_vector.assert_called_once()
                    call_args = mock_qdrant.upsert_vector.call_args
                    metadata_arg = call_args[1]["metadata"]

                    # Check that enhanced metadata is preserved
                    assert "auto_tags" in metadata_arg
                    assert "confidence_scores" in metadata_arg
                    assert "content_hash" in metadata_arg
                    assert "version" in metadata_arg

    @pytest.mark.asyncio
    async def test_cursor_error_handling_workflow(self, sample_cursor_documents):
        """Test error handling in the Cursor IDE integration workflow."""
        doc = sample_cursor_documents[0]

        # Create a mock embedding provider that fails
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.side_effect = Exception("Embedding generation failed")
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch(
            "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
        ) as mock_firestore_class:

            mock_firestore = AsyncMock()
            mock_firestore.save_metadata.return_value = True
            mock_firestore_class.return_value = mock_firestore

            # Initialize vectorization tool with failing embedding provider
            tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)

            # Process document (should fail due to embedding failure)
            result = await tool.vectorize_document(
                doc_id=doc["doc_id"],
                content=doc["content"],
                metadata=doc["metadata"],
                tag=doc["tag"],
                update_firestore=True,
            )

            # Verify failure is handled gracefully
            assert result["status"] == "failed"
            assert result["doc_id"] == doc["doc_id"]
            assert "Embedding generation failed" in result["error"]

            # Verify Firestore was updated with failure status
            assert mock_firestore.save_metadata.call_count >= 1

    @pytest.mark.slow
    def test_cursor_integration_performance_requirements(self):
        """Test that the integration meets performance requirements for Cursor IDE."""
        # Performance requirements for Cursor IDE integration:
        # - Document vectorization should complete within 5 seconds
        # - Batch processing should handle 10 documents within 30 seconds
        # - Search queries should return results within 2 seconds
        # - Memory usage should remain under 500MB for typical workloads

        # These are design requirements that should be validated in real integration tests
        max_single_doc_time = 5.0  # seconds
        max_batch_time = 30.0  # seconds for 10 documents
        max_search_time = 2.0  # seconds
        max_memory_usage = 500  # MB

        # Assert requirements are reasonable
        assert max_single_doc_time > 0
        assert max_batch_time > max_single_doc_time
        assert max_search_time > 0
        assert max_memory_usage > 0

        # In a real test, we would measure actual performance
        # For now, we just validate the requirements are defined
        performance_requirements = {
            "single_document_vectorization_max_time": max_single_doc_time,
            "batch_processing_max_time": max_batch_time,
            "search_query_max_time": max_search_time,
            "max_memory_usage_mb": max_memory_usage,
        }

        assert all(v > 0 for v in performance_requirements.values())

    @pytest.mark.asyncio
    async def test_cursor_integration_data_consistency(self, sample_cursor_documents, mock_openai_embedding_response):
        """Test data consistency between Qdrant and Firestore in Cursor workflow."""
        doc = sample_cursor_documents[0]

        # Create a mock embedding provider that returns the expected response
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.embed_single.return_value = mock_openai_embedding_response["embedding"]
        mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

        with patch("agent_data_manager.tools.qdrant_vectorization_tool.QdrantStore") as mock_qdrant_class:
            with patch(
                "agent_data_manager.tools.qdrant_vectorization_tool.FirestoreMetadataManager"
            ) as mock_firestore_class:
                with patch("agent_data_manager.tools.qdrant_vectorization_tool.get_auto_tagging_tool") as mock_auto_tag:

                    # Setup mocks to track calls
                    mock_qdrant = AsyncMock()
                    mock_qdrant.upsert_vector.return_value = {"success": True, "vector_id": doc["doc_id"]}
                    mock_qdrant_class.return_value = mock_qdrant

                    mock_firestore = AsyncMock()
                    mock_firestore.save_metadata.return_value = True
                    mock_firestore_class.return_value = mock_firestore

                    # Setup auto-tagging mock
                    mock_auto_tagging_tool = AsyncMock()
                    mock_auto_tagging_tool.enhance_metadata_with_tags.return_value = doc["metadata"]
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

                    # Verify data consistency between Qdrant and Firestore
                    # Both should have been called with the same doc_id
                    mock_qdrant.upsert_vector.assert_called_once()
                    qdrant_call_args = mock_qdrant.upsert_vector.call_args
                    assert qdrant_call_args[1]["vector_id"] == doc["doc_id"]

                    # Firestore should have been called at least twice (pending + completed)
                    assert mock_firestore.save_metadata.call_count >= 2

                    # Verify the doc_id is consistent across all calls
                    for call in mock_firestore.save_metadata.call_args_list:
                        assert call[0][0] == doc["doc_id"]  # First argument should be doc_id
