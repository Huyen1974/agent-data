"""
Test suite for Cursor IDE integration via MCP stdio
Tests enhanced document storage from Cursor IDE to Qdrant/Firestore
"""

import pytest
import json
from unittest.mock import AsyncMock

# Import the function we need to test
from agent_data_manager.local_mcp_server import handle_cursor_document_storage


class TestCursorIntegration:
    """Test class for Cursor IDE integration functionality"""

    @pytest.fixture
    def mock_vectorization_tool(self):
        """Mock QdrantVectorizationTool for testing"""
        mock = AsyncMock()
        mock.vectorize_document = AsyncMock(
            side_effect=lambda doc_id, content, metadata=None, tag=None, update_firestore=True: {
                "status": "success",
                "doc_id": doc_id,  # Return the actual doc_id passed in
                "vector_id": f"vec_{doc_id}",
                "embedding_dimension": 1536,
                "metadata_keys": ["doc_id", "content_preview", "vectorized_at", "source"],
                "firestore_updated": True,
            }
        )
        return mock

    @pytest.fixture
    def cursor_save_request(self):
        """Sample Cursor IDE save request"""
        return {
            "tool_name": "cursor_save_document",
            "kwargs": {
                "doc_id": "cursor_doc_001",
                "content": "This is a document saved from Cursor IDE for testing integration.",
                "save_dir": "ide_docs",
                "metadata": {
                    "source": "cursor_ide",
                    "timestamp": "2025-01-27T18:30:00Z",
                    "user": "test_developer",
                    "project": "agent_data_integration",
                },
            },
            "timestamp": "2025-01-27T18:30:00Z",
        }

    @pytest.fixture
    def minimal_cursor_request(self):
        """Minimal Cursor IDE save request"""
        return {
            "tool_name": "cursor_save_document",
            "kwargs": {"doc_id": "cursor_minimal_001", "content": "Minimal test document from Cursor."},
        }

    @pytest.mark.asyncio
    async def test_handle_cursor_document_storage_success(self, mock_vectorization_tool, cursor_save_request):
        """Test successful Cursor document storage"""
        result = await handle_cursor_document_storage(
            mock_vectorization_tool, cursor_save_request["tool_name"], cursor_save_request
        )

        # Verify result structure
        assert result["status"] == "success"
        assert result["doc_id"] == "cursor_doc_001"
        assert result["vector_id"] == "vec_cursor_doc_001"
        assert result["embedding_dimension"] == 1536
        assert result["firestore_updated"] is True

        # Verify Cursor-specific integration information
        cursor_info = result["cursor_integration"]
        assert cursor_info["save_dir"] == "ide_docs"
        assert cursor_info["original_doc_id"] == "cursor_doc_001"
        assert cursor_info["metadata_enhanced"] is True
        assert cursor_info["firestore_sync"] is True
        assert cursor_info["qdrant_tag"] == "cursor_ide_docs"

        # Verify the vectorization tool was called with enhanced metadata
        mock_vectorization_tool.vectorize_document.assert_called_once()
        call_args = mock_vectorization_tool.vectorize_document.call_args

        assert call_args[1]["doc_id"] == "cursor_doc_001"
        assert call_args[1]["tag"] == "cursor_ide_docs"
        assert call_args[1]["update_firestore"] is True

        # Check enhanced metadata
        metadata = call_args[1]["metadata"]
        assert metadata["source"] == "cursor_ide"
        assert metadata["save_directory"] == "ide_docs"
        assert metadata["integration_type"] == "mcp_stdio"
        assert "processed_at" in metadata

    @pytest.mark.asyncio
    async def test_handle_cursor_document_storage_minimal(self, mock_vectorization_tool, minimal_cursor_request):
        """Test Cursor document storage with minimal request"""
        result = await handle_cursor_document_storage(
            mock_vectorization_tool, minimal_cursor_request["tool_name"], minimal_cursor_request
        )

        assert result["status"] == "success"
        assert result["doc_id"] == "cursor_minimal_001"

        # Verify default values
        cursor_info = result["cursor_integration"]
        assert cursor_info["save_dir"] == "cursor_documents"  # Default value
        assert cursor_info["qdrant_tag"] == "cursor_cursor_documents"

        # Verify enhanced metadata includes defaults
        call_args = mock_vectorization_tool.vectorize_document.call_args
        metadata = call_args[1]["metadata"]
        assert metadata["source"] == "cursor_ide"
        assert metadata["save_directory"] == "cursor_documents"
        assert metadata["integration_type"] == "mcp_stdio"

    @pytest.mark.asyncio
    async def test_handle_cursor_document_storage_missing_doc_id(self, mock_vectorization_tool):
        """Test Cursor document storage with missing doc_id"""
        invalid_request = {"tool_name": "cursor_save_document", "kwargs": {"content": "Document without doc_id"}}

        with pytest.raises(ValueError, match="cursor_save_document requires 'doc_id' and 'content' in kwargs"):
            await handle_cursor_document_storage(mock_vectorization_tool, invalid_request["tool_name"], invalid_request)

    @pytest.mark.asyncio
    async def test_handle_cursor_document_storage_missing_content(self, mock_vectorization_tool):
        """Test Cursor document storage with missing content"""
        invalid_request = {"tool_name": "cursor_save_document", "kwargs": {"doc_id": "cursor_invalid_001"}}

        with pytest.raises(ValueError, match="cursor_save_document requires 'doc_id' and 'content' in kwargs"):
            await handle_cursor_document_storage(mock_vectorization_tool, invalid_request["tool_name"], invalid_request)

    @pytest.mark.asyncio
    async def test_handle_cursor_document_storage_vectorization_failure(self, cursor_save_request):
        """Test Cursor document storage when vectorization fails"""
        # Mock vectorization tool that returns failure
        mock_tool = AsyncMock()
        mock_tool.vectorize_document.return_value = {
            "status": "failed",
            "doc_id": "cursor_doc_001",
            "error": "Failed to generate embedding",
        }

        result = await handle_cursor_document_storage(mock_tool, cursor_save_request["tool_name"], cursor_save_request)

        # Should still return result but with failed status
        assert result["status"] == "failed"
        assert result["doc_id"] == "cursor_doc_001"
        assert result["error"] == "Failed to generate embedding"

        # Cursor integration info should still be present
        assert "cursor_integration" in result
        cursor_info = result["cursor_integration"]
        assert cursor_info["save_dir"] == "ide_docs"

    @pytest.mark.asyncio
    async def test_cursor_metadata_enhancement(self, mock_vectorization_tool, cursor_save_request):
        """Test that Cursor metadata is properly enhanced"""
        await handle_cursor_document_storage(
            mock_vectorization_tool, cursor_save_request["tool_name"], cursor_save_request
        )

        call_args = mock_vectorization_tool.vectorize_document.call_args
        enhanced_metadata = call_args[1]["metadata"]

        # Original metadata should be preserved
        assert enhanced_metadata["user"] == "test_developer"
        assert enhanced_metadata["project"] == "agent_data_integration"

        # Enhanced metadata should be added
        assert enhanced_metadata["source"] == "cursor_ide"
        assert enhanced_metadata["save_directory"] == "ide_docs"
        assert enhanced_metadata["integration_type"] == "mcp_stdio"
        assert "processed_at" in enhanced_metadata

    def test_cursor_json_format_compatibility(self):
        """Test that Cursor request format is compatible with JSON parsing"""
        cursor_json = {
            "tool_name": "cursor_save_document",
            "kwargs": {
                "doc_id": "cursor_compatibility_001",
                "content": "Testing JSON compatibility for Cursor IDE integration.",
                "save_dir": "compatibility_test",
                "metadata": {"source": "cursor_ide", "editor": "cursor", "language": "python"},
            },
        }

        # Should be serializable to JSON
        json_str = json.dumps(cursor_json)
        assert isinstance(json_str, str)

        # Should be deserializable from JSON
        parsed = json.loads(json_str)
        assert parsed["tool_name"] == "cursor_save_document"
        assert parsed["kwargs"]["doc_id"] == "cursor_compatibility_001"
        assert parsed["kwargs"]["metadata"]["editor"] == "cursor"

    @pytest.mark.asyncio
    async def test_cursor_integration_different_save_dirs(self, mock_vectorization_tool):
        """Test Cursor integration with different save directories"""
        test_cases = [
            ("project_docs", "cursor_project_docs"),
            ("user_notes", "cursor_user_notes"),
            ("", "cursor_"),  # Edge case with empty save_dir
            (None, "cursor_cursor_documents"),  # Default when save_dir is None
        ]

        for save_dir, expected_tag in test_cases:
            request = {
                "tool_name": "cursor_save_document",
                "kwargs": {
                    "doc_id": f"test_doc_{save_dir or 'default'}",
                    "content": f"Test document for save_dir: {save_dir}",
                    "save_dir": save_dir,
                },
            }

            # Handle None case (remove save_dir key entirely)
            if save_dir is None:
                del request["kwargs"]["save_dir"]

            result = await handle_cursor_document_storage(mock_vectorization_tool, request["tool_name"], request)

            cursor_info = result["cursor_integration"]
            assert cursor_info["qdrant_tag"] == expected_tag

            # Reset mock for next iteration
            mock_vectorization_tool.reset_mock()

    @pytest.mark.asyncio
    async def test_cursor_integration_real_world_scenario(self, mock_vectorization_tool):
        """Test a real-world scenario of Cursor IDE integration"""
        # Simulate a real Cursor IDE scenario where a developer saves a code snippet
        real_world_request = {
            "tool_name": "cursor_save_document",
            "kwargs": {
                "doc_id": "python_function_utils_20250127",
                "content": """
def calculate_similarity_score(vector1, vector2):
    '''Calculate cosine similarity between two vectors'''
    import numpy as np
    dot_product = np.dot(vector1, vector2)
    norms = np.linalg.norm(vector1) * np.linalg.norm(vector2)
    return dot_product / norms if norms != 0 else 0
                """.strip(),
                "save_dir": "code_snippets",
                "metadata": {
                    "source": "cursor_ide",
                    "file_type": "python",
                    "function_name": "calculate_similarity_score",
                    "created_by": "developer@company.com",
                    "purpose": "utility_function",
                    "project": "agent_data_system",
                },
            },
            "timestamp": "2025-01-27T18:30:15Z",
        }

        result = await handle_cursor_document_storage(
            mock_vectorization_tool, real_world_request["tool_name"], real_world_request
        )

        # Verify successful processing
        assert result["status"] == "success"
        assert result["doc_id"] == "python_function_utils_20250127"

        # Verify Cursor integration information
        cursor_info = result["cursor_integration"]
        assert cursor_info["save_dir"] == "code_snippets"
        assert cursor_info["qdrant_tag"] == "cursor_code_snippets"
        assert cursor_info["firestore_sync"] is True

        # Verify vectorization was called with correct parameters
        call_args = mock_vectorization_tool.vectorize_document.call_args
        assert call_args[1]["doc_id"] == "python_function_utils_20250127"
        assert call_args[1]["tag"] == "cursor_code_snippets"
        assert "calculate_similarity_score" in call_args[1]["content"]

        # Check metadata enhancement
        metadata = call_args[1]["metadata"]
        assert metadata["source"] == "cursor_ide"
        assert metadata["save_directory"] == "code_snippets"
        assert metadata["integration_type"] == "mcp_stdio"
        assert metadata["function_name"] == "calculate_similarity_score"
        assert metadata["file_type"] == "python"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
