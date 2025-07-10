import re

file_path = "tests/tools/test_save_metadata_to_faiss.py"

new_func = """
@patch(f"{SAVE_TOOL_MODULE_PATH}.OPENAI_AVAILABLE", True)
@patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
@patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
@patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
@patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
@patch(FIRESTORE_CLIENT_PATH)
@patch(UPLOAD_WITH_RETRY_PATH)
@patch(STORAGE_CLIENT_SAVE_PATH)
async def test_save_firestore_client_init_fails(self,
    MockFaissIndexFlatL2,
    mock_faiss_write_index,
    mock_pickle_dump,
    mock_firestore_constructor,
    mock_upload_with_retry,
    mock_storage_client_constructor,
    mocker, request):
    \"\"\"Test failure during Firestore client initialization.\"\"\"
    from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

    mock_firestore_constructor.side_effect = google_exceptions.GoogleCloudError("Mocked Firestore client init failed")

    input_data = {
        "index_name": "test_fs_init_fail_index",
        "metadata_dict": {"doc1": {"text": "Some text"}},
        "text_field_to_embed": "text",
        "dimension": 10
    }

    result = await save_metadata_to_faiss(**input_data)

    assert result is not None
    assert result.get("status") == "error"
    assert "Failed to initialize Firestore client" in result.get("message", "")
    assert result.get("meta", {}).get("error_type") in [
        "GoogleCloudError", "ConfigurationError", "FirestoreError", "FirestoreInitializationError"
    ]
    assert result.get("meta", {}).get("index_name") == "test_fs_init_fail_index"
    assert "vector_count" not in result.get("meta", {})
    assert "dimension" not in result.get("meta", {})

    mock_firestore_constructor.assert_called_once()
    mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2").assert_not_called()
    mocker.patch(UPLOAD_WITH_RETRY_PATH).assert_not_called()
"""

pattern = r"@patch\(f\"{SAVE_TOOL_MODULE_PATH}\.OPENAI_AVAILABLE\", True\)[\s\S]+?async def test_save_firestore_client_init_fails\(self,[\s\S]+?\"\"\"Test failure during Firestore client initialization.\"\"\"[\s\S]+?mocker\.patch\(UPLOAD_WITH_RETRY_PATH\)\.assert_not_called\(\)"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

content, n = re.subn(pattern, new_func.strip(), content, flags=re.MULTILINE)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Đã thay thế function test_save_firestore_client_init_fails (số lần thay thế: {n})")
