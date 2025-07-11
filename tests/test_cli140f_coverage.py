"""
Test coverage for qdrant_vectorization_tool.py - CLI140f
Target: Increase coverage from 38% to ≥50% with 1-2 new performance tests
Focus: Simple functions, factory methods, and edge cases without complex dependencies
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

# Import from src since that's what the existing tests use
from src.agent_data_manager.tools.qdrant_vectorization_tool import (
    QdrantVectorizationTool,
    get_vectorization_tool,
    qdrant_batch_vectorize_documents,
    qdrant_rag_search,
    qdrant_vectorize_document,
)


@pytest.mark.performance
@pytest.mark.asyncio
class TestCLI140fCoverage:
    """Test class for CLI140f coverage improvement - simple functions and edge cases."""

    def setup_method(self):
        """Setup for each test method."""
        self.mock_embedding_provider = AsyncMock()
        self.mock_embedding_provider.embed_single.return_value = [0.1] * 1536
        self.mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"

    @pytest.mark.asyncio
    async def test_batch_vectorize_simple_edge_cases(self):
        """Test batch vectorization with simple edge cases."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Mock initialization and settings to avoid complex dependencies
        with patch.object(tool, "_ensure_initialized") as mock_init, \
             patch("src.agent_data_manager.tools.qdrant_vectorization_tool.settings") as mock_settings:
            
            mock_init.return_value = None
            tool.qdrant_store = AsyncMock()
            tool.firestore_manager = AsyncMock()
            tool.qdrant_store.upsert_vector.return_value = {"success": True, "vector_id": "test_vector"}
            
            # Mock settings for batch configuration
            mock_settings.get_qdrant_config.return_value = {
                "batch_size": 100,
                "sleep_between_batches": 0.35
            }

            # Test edge case: empty documents list
            result = await tool.batch_vectorize_documents([], tag="test_tag")
            assert result["status"] == "completed"
            assert result["total_documents"] == 0
            assert result["successful"] == 0
            assert result["failed"] == 0

            # Test edge case: single document
            single_doc = [{"doc_id": "single_test", "content": "Single test content"}]
            
            # Mock vectorize_document to avoid complex dependencies
            with patch.object(tool, "vectorize_document") as mock_vectorize:
                mock_vectorize.return_value = {"status": "success", "doc_id": "single_test"}
                
                result = await tool.batch_vectorize_documents(single_doc, tag="single_tag", update_firestore=False)
                assert result["status"] == "completed"
                assert result["total_documents"] == 1
                assert result["successful"] == 1
                assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_rate_limiting_mechanism(self):
        """Test rate limiting mechanism without complex dependencies."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Test rate limiter initialization
        assert "last_call" in tool._rate_limiter
        assert "min_interval" in tool._rate_limiter
        assert tool._rate_limiter["min_interval"] == 0.3  # 300ms

        # Test rate limiting behavior
        start_time = time.time()
        await tool._rate_limit()
        first_call_time = time.time()

        await tool._rate_limit()
        second_call_time = time.time()

        # Second call should be delayed by at least min_interval
        time_diff = second_call_time - first_call_time
        assert time_diff >= 0.25  # Allow some tolerance for timing

    @pytest.mark.asyncio
    async def test_filter_methods_coverage(self):
        """Test the filter methods for better coverage."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)

        # Test data for filtering
        sample_results = [
            {
                "auto_tags": ["tag1", "tag2"], 
                "category": "test", 
                "level_1_category": "cat1",
                "level_2_category": "subcat1"
            },
            {
                "auto_tags": ["tag3"], 
                "category": "other", 
                "level_1_category": "cat2",
                "level_3_category": "subcat2"
            },
            {
                "auto_tags": ["tag1"], 
                "category": "test", 
                "level_2_category": "subcat1"
            },
        ]

        # Test metadata filtering
        filtered_by_metadata = tool._filter_by_metadata(sample_results, {"category": "test"})
        assert len(filtered_by_metadata) == 2

        # Test empty metadata filters
        filtered_empty = tool._filter_by_metadata(sample_results, {})
        assert len(filtered_empty) == 3

        # Test tag filtering
        filtered_by_tags = tool._filter_by_tags(sample_results, ["tag1"])
        assert len(filtered_by_tags) == 2

        # Test path filtering
        filtered_by_path = tool._filter_by_path(sample_results, "cat1")
        assert len(filtered_by_path) >= 1  # At least one result contains "cat1"

        # Test hierarchy path building
        hierarchy_path = tool._build_hierarchy_path(sample_results[0])
        assert "cat1" in hierarchy_path
        assert "subcat1" in hierarchy_path

    @pytest.mark.asyncio
    async def test_simple_initialization_coverage(self):
        """Test simple initialization and basic methods for coverage."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)
        
        # Test initialization state
        assert not tool._initialized
        assert tool.embedding_provider is self.mock_embedding_provider
        
        # Test rate limiter properties
        assert tool._rate_limiter["min_interval"] == 0.3
        
        # Test filter methods with edge cases
        empty_results = []
        filtered = tool._filter_by_metadata(empty_results, {"test": "value"})
        assert filtered == []
        
        filtered = tool._filter_by_tags(empty_results, ["tag1"])
        assert filtered == []
        
        filtered = tool._filter_by_path(empty_results, "test_path")
        assert filtered == []
        
        # Test hierarchy path with empty result
        empty_result = {}
        path = tool._build_hierarchy_path(empty_result)
        assert path == "Uncategorized"
        
        # Test with partial hierarchy
        partial_result = {"level_1_category": "cat1", "level_3_category": "cat3"}
        path = tool._build_hierarchy_path(partial_result)
        assert "cat1" in path
        assert "cat3" in path

    @pytest.mark.asyncio
    async def test_batch_get_firestore_metadata_coverage(self):
        """Test batch Firestore metadata retrieval for coverage improvement."""
        tool = QdrantVectorizationTool(embedding_provider=self.mock_embedding_provider)
        
        # Test with no firestore manager
        tool.firestore_manager = None
        result = await tool._batch_get_firestore_metadata(["doc1", "doc2"])
        assert result == {}
        
        # Test with mock firestore manager that has batch_get_metadata
        mock_firestore = AsyncMock()
        mock_firestore.batch_get_metadata.return_value = {
            "doc1": {"metadata": "test1"},
            "doc2": {"metadata": "test2"}
        }
        tool.firestore_manager = mock_firestore
        
        result = await tool._batch_get_firestore_metadata(["doc1", "doc2"])
        assert "doc1" in result
        assert "doc2" in result
        assert result["doc1"]["metadata"] == "test1"
        
        # Test fallback to individual queries
        mock_firestore_no_batch = AsyncMock()
        # Remove batch_get_metadata method to trigger fallback
        del mock_firestore_no_batch.batch_get_metadata
        mock_firestore_no_batch.get_metadata_with_version.return_value = {"fallback": "test"}
        tool.firestore_manager = mock_firestore_no_batch
        
        result = await tool._batch_get_firestore_metadata(["doc3"])
        # Should handle the fallback gracefully
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_standalone_function_coverage(self):
        """Test standalone functions for additional coverage."""
        # Clear global instance
        import src.agent_data_manager.tools.qdrant_vectorization_tool as module
        module._vectorization_tool = None
        
        # Test qdrant_vectorize_document function
        with patch.object(QdrantVectorizationTool, "vectorize_document") as mock_vectorize:
            mock_vectorize.return_value = {"status": "success", "doc_id": "test_doc"}
            
            result = await qdrant_vectorize_document(
                doc_id="test_doc",
                content="test content",
                metadata={"test": "metadata"},
                tag="test_tag",
                update_firestore=False
            )
            
            assert result["status"] == "success"
            assert result["doc_id"] == "test_doc"
            mock_vectorize.assert_called_once()


@pytest.mark.performance
@pytest.mark.unit
def test_get_vectorization_tool_factory_performance():
    """Test the factory function for creating vectorization tools with performance validation."""
    # Clear the global instance first
    import src.agent_data_manager.tools.qdrant_vectorization_tool as module
    module._vectorization_tool = None
    
    # Test default creation
    start_time = time.time()
    tool = get_vectorization_tool()
    end_time = time.time()

    creation_time = end_time - start_time
    assert creation_time < 0.1, f"Tool creation took {creation_time:.3f}s, should be <0.1s"
    assert isinstance(tool, QdrantVectorizationTool)
    assert tool.embedding_provider is None  # Should be None until initialized

    # Test that subsequent calls return the same instance
    tool2 = get_vectorization_tool()
    assert tool is tool2  # Should be the same instance

    # Clear global instance and test creation with custom embedding provider
    module._vectorization_tool = None
    mock_provider = MagicMock()
    tool_with_provider = get_vectorization_tool(embedding_provider=mock_provider)
    assert tool_with_provider.embedding_provider is mock_provider


@pytest.mark.performance
@pytest.mark.asyncio
async def test_qdrant_batch_vectorize_documents_function_performance():
    """Test the standalone batch vectorize function with performance validation."""
    # Clear global instance
    import src.agent_data_manager.tools.qdrant_vectorization_tool as module
    module._vectorization_tool = None
    
    # Mock the batch_vectorize_documents method
    with patch.object(QdrantVectorizationTool, "batch_vectorize_documents") as mock_batch:
        mock_batch.return_value = {
            "status": "completed",
            "total_documents": 2,
            "successful": 2,
            "failed": 0,
            "results": []
        }
        
        documents = [
            {"doc_id": "doc1", "content": "content1"},
            {"doc_id": "doc2", "content": "content2"}
        ]
        
        start_time = time.time()
        result = await qdrant_batch_vectorize_documents(
            documents=documents,
            tag="test_batch",
            update_firestore=False
        )
        end_time = time.time()
        
        # Performance validation
        execution_time = end_time - start_time
        assert execution_time < 0.1, f"Batch function took {execution_time:.3f}s, should be <0.1s"
        
        # Result validation
        assert result["status"] == "completed"
        assert result["total_documents"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        
        # Verify the method was called with correct parameters
        mock_batch.assert_called_once_with(documents, "test_batch", False)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_qdrant_rag_search_function_performance():
    """Test the standalone RAG search function with performance validation."""
    # Clear global instance
    import src.agent_data_manager.tools.qdrant_vectorization_tool as module
    module._vectorization_tool = None
    
    # Mock the rag_search method
    with patch.object(QdrantVectorizationTool, "rag_search") as mock_rag:
        mock_rag.return_value = {
            "status": "success",
            "query": "test query",
            "results": [],
            "total_results": 0,
            "search_time": 0.05
        }
        
        start_time = time.time()
        result = await qdrant_rag_search(
            query_text="test query",
            metadata_filters={"category": "test"},
            tags=["tag1"],
            path_query="test_path",
            limit=5,
            score_threshold=0.7,
            qdrant_tag="test_qdrant_tag"
        )
        end_time = time.time()
        
        # Performance validation
        execution_time = end_time - start_time
        assert execution_time < 0.1, f"RAG search function took {execution_time:.3f}s, should be <0.1s"
        
        # Result validation
        assert result["status"] == "success"
        assert result["query"] == "test query"
        assert "results" in result
        
        # Verify the method was called with correct parameters
        mock_rag.assert_called_once_with(
            query_text="test query",
            metadata_filters={"category": "test"},
            tags=["tag1"],
            path_query="test_path",
            limit=5,
            score_threshold=0.7,
            qdrant_tag="test_qdrant_tag"
        ) 