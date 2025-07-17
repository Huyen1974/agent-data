
test_code = '''
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    async def test_save_vector_data_count_mismatch(self, MockFaissIndexFlatL2, mocker, request):
        """Test error when len(vector_data) != len(doc_ids_from_metadata)."""
        from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mocker.patch(FIRESTORE_CLIENT_PATH)
        mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.OPENAI_AVAILABLE", True)
        mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())

        input_data = {
            "index_name": "test_vector_count_mismatch",
            "metadata_dict": {
                "doc1": {"description": "Document 1"},
                "doc2": {"description": "Document 2"}
            },
            "vector_data": [
                [0.1] * 10
            ],
            "dimension": 10
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert result.get("status") == "error"
        # The message check needs to be aligned with actual number of docs from metadata_dict
        # doc_ids_to_process will be ['doc1', 'doc2'] so count is 2. vector_data has 1.
        assert "Mismatch between number of documents (2) and provided vectors (1)" in result.get("message", "")
        assert result.get("meta", {}).get("error_type") == "InvalidVectorDataError"
        assert result.get("meta", {}).get("index_name") == "test_vector_count_mismatch"
        MockFaissIndexFlatL2.assert_not_called()
'''

# Thêm vào cuối file test_save_metadata_to_faiss.py
target_file = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tests/tools/test_save_metadata_to_faiss.py"

with open(target_file, "a", encoding="utf-8") as f:
    f.write("\n" + test_code + "\n")

print(
    "✅ Đã chèn test test_save_vector_data_count_mismatch vào file test_save_metadata_to_faiss.py"
)
