"""
CLI140f Coverage Tests - Performance tests for qdrant_vectorization_tool.py
Target: Increase coverage from 38% to ≥50% with 2 new performance tests
Focus: Simple functions and edge cases without complex dependencies
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock

# Import from src since that's what the existing tests use
from src.agent_data_manager.tools.qdrant_vectorization_tool import (
    QdrantVectorizationTool,
    get_vectorization_tool,
    qdrant_vectorize_document,
)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_cli140f_batch_firestore_metadata_performance():
    """CLI140f Test 1: Test batch Firestore metadata retrieval for coverage improvement."""
    mock_embedding_provider = AsyncMock()
    mock_embedding_provider.embed_single.return_value = [0.1] * 1536
    mock_embedding_provider.get_model_name.return_value = "text-embedding-ada-002"
    
    tool = QdrantVectorizationTool(embedding_provider=mock_embedding_provider)
    
    # Test with no firestore manager
    tool.firestore_manager = None
    start_time = time.time()
    result = await tool._batch_get_firestore_metadata(["doc1", "doc2"])
    end_time = time.time()
    
    # Performance validation
    execution_time = end_time - start_time
    assert execution_time < 0.1, f"Batch metadata retrieval took {execution_time:.3f}s, should be <0.1s"
    assert result == {}
    
    # Test with mock firestore manager that has batch_get_metadata
    mock_firestore = AsyncMock()
    mock_firestore.batch_get_metadata.return_value = {
        "doc1": {"metadata": "test1", "vectorStatus": "completed"},
        "doc2": {"metadata": "test2", "vectorStatus": "pending"}
    }
    tool.firestore_manager = mock_firestore
    
    start_time = time.time()
    result = await tool._batch_get_firestore_metadata(["doc1", "doc2"])
    end_time = time.time()
    
    # Performance validation
    execution_time = end_time - start_time
    assert execution_time < 0.1, f"Batch metadata retrieval took {execution_time:.3f}s, should be <0.1s"
    assert "doc1" in result
    assert "doc2" in result
    assert result["doc1"]["metadata"] == "test1"
    assert result["doc2"]["vectorStatus"] == "pending"
    
    # Test fallback to individual queries
    mock_firestore_no_batch = AsyncMock()
    # Remove batch_get_metadata method to trigger fallback
    del mock_firestore_no_batch.batch_get_metadata
    mock_firestore_no_batch.get_metadata_with_version.return_value = {"fallback": "test", "vectorStatus": "completed"}
    tool.firestore_manager = mock_firestore_no_batch
    
    start_time = time.time()
    result = await tool._batch_get_firestore_metadata(["doc3"])
    end_time = time.time()
    
    # Performance validation for fallback
    execution_time = end_time - start_time
    assert execution_time < 0.5, f"Fallback metadata retrieval took {execution_time:.3f}s, should be <0.5s"
    assert isinstance(result, dict)


@pytest.mark.performance
@pytest.mark.asyncio
async def test_cli140f_standalone_function_performance():
    """CLI140f Test 2: Test standalone functions for additional coverage and performance."""
    # Clear global instance
    import src.agent_data_manager.tools.qdrant_vectorization_tool as module
    module._vectorization_tool = None
    
    # Test qdrant_vectorize_document function performance
    with patch.object(QdrantVectorizationTool, "vectorize_document") as mock_vectorize:
        mock_vectorize.return_value = {
            "status": "success", 
            "doc_id": "test_doc",
            "vector_id": "vec_123",
            "embedding_dimension": 1536,
            "firestore_updated": False
        }
        
        start_time = time.time()
        result = await qdrant_vectorize_document(
            doc_id="test_doc",
            content="test content for performance validation",
            metadata={"test": "metadata", "category": "performance"},
            tag="cli140f_test",
            update_firestore=False
        )
        end_time = time.time()
        
        # Performance validation
        execution_time = end_time - start_time
        assert execution_time < 0.1, f"Standalone vectorize function took {execution_time:.3f}s, should be <0.1s"
        
        # Result validation
        assert result["status"] == "success"
        assert result["doc_id"] == "test_doc"
        assert result["vector_id"] == "vec_123"
        assert result["embedding_dimension"] == 1536
        mock_vectorize.assert_called_once()
        
        # Verify call arguments
        call_args = mock_vectorize.call_args
        # Check if arguments are positional or keyword
        if call_args[0]:  # Positional arguments
            assert call_args[0][0] == "test_doc"  # doc_id
            assert call_args[0][1] == "test content for performance validation"  # content
        else:  # Keyword arguments
            assert call_args[1]["doc_id"] == "test_doc"
            assert call_args[1]["content"] == "test content for performance validation"
            assert call_args[1]["metadata"]["category"] == "performance"
            assert call_args[1]["tag"] == "cli140f_test"
            assert call_args[1]["update_firestore"] == False
    
    # Test factory function performance with different scenarios
    module._vectorization_tool = None
    
    # Test default creation performance
    start_time = time.time()
    tool1 = get_vectorization_tool()
    end_time = time.time()
    
    creation_time = end_time - start_time
    assert creation_time < 0.05, f"Tool creation took {creation_time:.3f}s, should be <0.05s"
    assert isinstance(tool1, QdrantVectorizationTool)
    assert tool1.embedding_provider is None
    
    # Test singleton behavior performance
    start_time = time.time()
    tool2 = get_vectorization_tool()
    end_time = time.time()
    
    singleton_time = end_time - start_time
    assert singleton_time < 0.01, f"Singleton access took {singleton_time:.3f}s, should be <0.01s"
    assert tool1 is tool2  # Should be the same instance
    
    # Test creation with custom provider
    module._vectorization_tool = None
    mock_provider = MagicMock()
    mock_provider.get_model_name.return_value = "custom-model"
    
    start_time = time.time()
    tool_with_provider = get_vectorization_tool(embedding_provider=mock_provider)
    end_time = time.time()
    
    custom_creation_time = end_time - start_time
    assert custom_creation_time < 0.05, f"Custom tool creation took {custom_creation_time:.3f}s, should be <0.05s"
    assert tool_with_provider.embedding_provider is mock_provider 