import re

filepath = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/tests/tools/test_save_metadata_to_faiss.py"

# Nội dung test mới, indent 4 dấu cách
new_test = """
    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())  # To pass OpenAI check
    @patch(f"{SAVE_TOOL_MODULE_PATH}.OPENAI_AVAILABLE", True)     # To pass OpenAI check
    @patch(FIRESTORE_CLIENT_PATH)
    async def test_save_firestore_client_init_fails(self, mock_firestore_constructor, mock_oai_available, mock_oai_client, mocker, request):
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

        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "Failed to initialize Firestore client" in result.get("message", "")
        assert result.get("meta", {}).get("error_type") in ["GoogleCloudError", "ConfigurationError", "FirestoreError"]
        assert result.get("meta", {}).get("index_name") == "test_fs_init_fail_index"
        mock_firestore_constructor.assert_called_once()
"""

with open(filepath, encoding="utf-8") as f:
    content = f.read()

# Tìm vị trí đóng class TestSaveMetadataToFaiss
pattern = r"(class TestSaveMetadataToFaiss.*?)(\n})"
match = re.search(
    r"(class TestSaveMetadataToFaiss[\s\S]+?)(\n})", content, re.MULTILINE
)
if match:
    new_content = content[: match.end(1)] + new_test + content[match.end(1) :]
else:
    # Nếu không tìm thấy thì thêm vào cuối file (an toàn)
    new_content = content.rstrip() + "\n" + new_test

with open(filepath, "w", encoding="utf-8") as f:
    f.write(new_content)

print(
    "✅ Đã chèn test test_save_firestore_client_init_fails vào file test_save_metadata_to_faiss.py"
)
