import re

file_path = "ADK/agent_data/tests/tools/test_save_metadata_to_faiss.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Thay đổi khai báo hàm (gộp lại đúng số biến mock như các test khác)
pattern_def = r"async def test_save_malformed_embedding_result\([^\)]*\):"
replace_def = "async def test_save_malformed_embedding_result(self, MockFaissIndexFlatL2, mock_faiss_write_index, mock_pickle_dump, mock_firestore_constructor, mock_upload_with_retry, mock_storage_client_constructor, mocker, request):"
content, n_def = re.subn(pattern_def, replace_def, content)

# 2. Xoá dòng mock_get_embedding.side_effect = ... (do không còn decorator mock_get_embedding ở trên)
pattern_side_effect = r"\s*mock_get_embedding\.side_effect\s*=\s*\[[\s\S]+?\]\n"
content, n_side = re.subn(pattern_side_effect, "", content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Đã sửa {n_def} khai báo hàm và xóa {n_side} dòng mock_get_embedding.side_effect")
