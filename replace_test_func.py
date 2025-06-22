import re

file_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tests/tools/test_save_metadata_to_faiss.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

new_func = """
@patch(f"{SAVE_TOOL_MODULE_PATH}.OPENAI_AVAILABLE", True)
@patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
@patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
@patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
@patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
@patch(FIRESTORE_CLIENT_PATH)
@patch(UPLOAD_WITH_RETRY_PATH)
@patch(STORAGE_CLIENT_SAVE_PATH)
async def test_save_malformed_embedding_result(self,
    MockFaissIndexFlatL2,
    mock_faiss_write_index,
    mock_pickle_dump,
    mock_firestore_constructor,
    mock_upload_with_retry,
    mock_storage_client_constructor,
    mocker, request):
    \"\"\"Test handling of malformed (but not exception-raising) embedding results.\"\"\"
    from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

    mock_fs_instance = mock_firestore_constructor.return_value
    mock_collection_ref = mock_fs_instance.collection.return_value
    mock_doc_ref = mock_collection_ref.document.return_value

    mock_storage_client_instance = mock_storage_client_constructor.return_value
    mock_bucket_instance = mock_storage_client_instance.bucket.return_value

    mock_upload_with_retry.return_value = MagicMock()

    mock_index_instance = MockFaissIndexFlatL2.return_value

    mock_get_embedding = mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding")
    mock_get_embedding.side_effect = [
        {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"},
        {"status": "success", "total_tokens": 0},
        "This is not a dictionary"
    ]

    input_metadata = {
        "doc1": {"text": "Valid text for doc1"},
        "doc2": {"text": "Text for doc2 (malformed: missing embedding key)"},
        "doc3": {"text": "Text for doc3 (malformed: not a dict)"}
    }
    input_data = {
        "index_name": "test_malformed_embed_index",
        "metadata_dict": input_metadata,
        "text_field_to_embed": "text",
        "dimension": 10
    }

    result = await save_metadata_to_faiss(**input_data)

    assert result is not None
    assert result.get("status") == "success"
    assert result.get("index_name") == "test_malformed_embed_index"
    assert result.get("vector_count") == 1
    assert result["dimension"] == 10
    assert result.get("gcs_upload_status") == "success"
    assert result.get("firestore_update_status") == "success"

    assert "meta" in result
    assert result["meta"].get("embedded_docs_count") == 1
    failed_doc_ids = result["meta"].get("failed_doc_ids", [])
    assert "doc2" in failed_doc_ids
    assert "doc3" in failed_doc_ids
    assert len(failed_doc_ids) == 2

    embedding_errors = result["meta"].get("embedding_generation_errors", {})
    assert "doc2" in embedding_errors
    assert "Malformed embedding result or non-success status for doc_id doc2" in embedding_errors["doc2"]
    assert "doc3" in embedding_errors
    assert "Malformed embedding result or non-success status for doc_id doc3" in embedding_errors["doc3"]

    mock_get_embedding.assert_has_calls([
        call(agent_context=None, text_to_embed="Valid text for doc1"),
        call(agent_context=None, text_to_embed="Text for doc2 (malformed: missing embedding key)"),
        call(agent_context=None, text_to_embed="Text for doc3 (malformed: not a dict)")
    ], any_order=True)
    assert mock_get_embedding.call_count == 3

    MockFaissIndexFlatL2.assert_called_once_with(10)
    mock_index_instance.add.assert_called_once()
    added_vectors = mock_index_instance.add.call_args[0][0]
    assert np.array_equal(added_vectors, np.array([[0.1]*10], dtype=np.float32))

    mock_faiss_write_index.assert_called_once()
    expected_pickle_data = {
        'ids': ['doc1'],
        'metadata': {'doc1': input_metadata['doc1']}
    }
    mock_pickle_dump.assert_called_once_with(expected_pickle_data, mocker.ANY)
    assert mock_upload_with_retry.call_count == 2

    mock_storage_client_constructor.assert_called_once_with(project="chatgpt-db-project")
    mock_storage_client_instance.bucket.assert_called_once_with(MOCKED_ENV_VARS["GCS_BUCKET_NAME"])

    mock_bucket_instance.blob.assert_has_calls([
        call(f"{input_data['index_name']}.faiss"),
        call(f"{input_data['index_name']}.meta")
    ], any_order=True)
    assert mock_bucket_instance.blob.call_count == 2

    mock_firestore_constructor.assert_called_once()
    mock_fs_instance.collection.assert_called_once_with(MOCKED_ENV_VARS["FAISS_INDEXES_COLLECTION"])
    mock_collection_ref.document.assert_called_once_with(input_data["index_name"])
    mock_doc_ref.set.assert_called_once()
    actual_set_call_args = mock_doc_ref.set.call_args[0][0]
    assert actual_set_call_args.get("vectorCount") == 1
"""

pattern = r"@patch\(f\"{SAVE_TOOL_MODULE_PATH}\.OPENAI_AVAILABLE\", True\)[\s\S]+?async def test_save_malformed_embedding_result[^\n]*\([\s\S]+?^\s+assert actual_set_call_args\.get\(\"vectorCount\"\) == 1"
content, n = re.subn(pattern, new_func.strip(), content, flags=re.MULTILINE)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Đã thay thế function test_save_malformed_embedding_result (số lần thay thế: {n})")
