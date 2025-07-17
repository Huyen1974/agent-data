test_code = '''
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    async def test_save_vector_data_invalid_item_type(self, MockFaissIndexFlatL2, mocker, request):
        """Test error when vector_data contains items that are not lists or numpy arrays."""
        from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mocker.patch(FIRESTORE_CLIENT_PATH)
        mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.OPENAI_AVAILABLE", True)
        mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())

        input_data = {
            "index_name": "test_vector_invalid_item_type",
            "metadata_dict": {"doc1": {"description": "Document 1"}},
            "vector_data": ["not a list or np.ndarray"], # Invalid item
            "dimension": 10
        }
        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "Vector data must be a list of lists or NumPy arrays." in result.get("message", "")
        assert result.get("meta", {}).get("error_type") == "InvalidVectorDataError"
        MockFaissIndexFlatL2.assert_not_called()
'''

target_file = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tests/tools/test_save_metadata_to_faiss.py"

with open(target_file, "a", encoding="utf-8") as f:
    f.write("\n" + test_code + "\n")

print(
    "✅ Đã chèn test test_save_vector_data_invalid_item_type vào file test_save_metadata_to_faiss.py"
)
