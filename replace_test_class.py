import re

# Đường dẫn file test cần thay
file_path = "ADK/agent_data/tests/tools/test_save_metadata_to_faiss.py"

# Đoạn mã mới thay thế (copy nguyên khối dưới đây)
replacement = """
import numpy as np
from unittest.mock import MagicMock, patch
import google.api_core.exceptions as api_core_exceptions
from google.cloud import storage
import google.cloud.exceptions as google_exceptions
from pytest_mock import MockerFixture
import pytest

SAVE_TOOL_MODULE_PATH = "agent_data_manager.tools.save_metadata_to_faiss_tool"
FIRESTORE_CLIENT_PATH = "agent_data_manager.tools.save_metadata_to_faiss_tool.firestore.Client"
UPLOAD_WITH_RETRY_PATH = "agent_data_manager.tools.save_metadata_to_faiss_tool.upload_with_retry"
STORAGE_CLIENT_SAVE_PATH = "agent_data_manager.tools.save_metadata_to_faiss_tool.storage.Client"

class TestSaveMetadataToFaiss:
    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=pytest_asyncio.plugin.AsyncMock)
    async def test_save_openai_embedding_error(self,
                                               mock_get_embedding,
                                               mock_faiss_write_index,
                                               mock_pickle_dump,
                                               mocker: MockerFixture,
                                               request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH, return_value=MagicMock())
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)

        from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss, EmbeddingGenerationError

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Correct mock for get_openai_embedding
        mock_get_embedding.side_effect = [
            {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"},
            EmbeddingGenerationError("Simulated embedding error for doc2")
        ]

        input_metadata = {
            "doc1": {"text": "Text that will succeed"},
            "doc2": {"text": "Text that will cause embedding error"}
        }
        input_data = {
            "index_name": "test_openai_error_index",
            "metadata_dict": input_metadata,
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(**input_data)
        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "success"  # One doc succeeds

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=pytest_asyncio.plugin.AsyncMock)
    async def test_save_gcs_upload_faiss_fails(self,
                                               mock_get_embedding,
                                               mock_faiss_write_index,
                                               mock_pickle_dump,
                                               mocker: MockerFixture,
                                               request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        def upload_side_effect(blob, source_file_name):
            if source_file_name.endswith(".faiss"):
                raise google_exceptions.NotFound("Mocked GCS FAISS upload failed")
            return None

        mock_upload_with_retry_local.side_effect = upload_side_effect

        input_data = {
            "index_name": "test_index_gcs_upload_fails",
            "metadata_dict": {"doc1": {"text": "Hello world"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(**input_data)
        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "Mocked GCS FAISS upload failed" in result["message"]

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=pytest_asyncio.plugin.AsyncMock)
    async def test_save_gcs_upload_meta_fails(self,
                                              mock_get_embedding,
                                              mock_faiss_write_index,
                                              mock_pickle_dump,
                                              mocker: MockerFixture,
                                              request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        def upload_side_effect_meta_fail(blob, source_file_name):
            if source_file_name.endswith(".meta"):
                raise google_exceptions.NotFound("Mocked GCS META upload failed")
            return None

        mock_upload_with_retry_local.side_effect = upload_side_effect_meta_fail

        input_data = {
            "index_name": "test_index_gcs_meta_upload_fails",
            "metadata_dict": {"doc1": {"text": "Hello world for meta fail"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(**input_data)
        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "Mocked GCS META upload failed" in result["message"]

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=pytest_asyncio.plugin.AsyncMock)
    async def test_save_firestore_update_fails(self,
                                               mock_get_embedding,
                                               mock_faiss_write_index,
                                               mock_pickle_dump,
                                               mocker: MockerFixture,
                                               request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH, return_value=MagicMock())
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value
        mock_doc_ref.set.side_effect = api_core_exceptions.Aborted("Mocked Firestore update failed")

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        input_data = {
            "index_name": "test_firestore_fail_index",
            "metadata_dict": {"doc1": {"text": "Firestore test text"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(**input_data)
        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert result.get("status") == "partial_success"

    @patch(f"{SAVE_TOOL_MODULE_PATH}.OPENAI_AVAILABLE", True)
    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(FIRESTORE_CLIENT_PATH)
    @patch(UPLOAD_WITH_RETRY_PATH)
    @patch(STORAGE_CLIENT_SAVE_PATH)
    async def test_save_firestore_client_init_fails(self,
                                                    mock_storage_client_constructor,
                                                    mock_upload_with_retry,
                                                    mock_firestore_constructor,
                                                    mock_pickle_dump,
                                                    mock_faiss_write_index,
                                                    mocker: MockerFixture,
                                                    request):
        from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mock_firestore_constructor.side_effect = google_exceptions.GoogleCloudError("Mocked Firestore client init failed")

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client_constructor.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

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
        assert result.get("meta", {}).get("error_type") in ["GoogleCloudError", "ConfigurationError", "FirestoreError", "FirestoreInitializationError"]

    @patch(f"{SAVE_TOOL_MODULE_PATH}.os.remove")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.os.path.exists", return_value=True)
    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=pytest_asyncio.plugin.AsyncMock)
    @patch(FIRESTORE_CLIENT_PATH)
    @patch(UPLOAD_WITH_RETRY_PATH)
    @patch(STORAGE_CLIENT_SAVE_PATH)
    async def test_save_temp_file_deletion_fails(self,
                                                 mock_os_remove,
                                                 mock_os_path_exists,
                                                 mock_pickle_dump,
                                                 mock_faiss_write_index,
                                                 mock_get_embedding,
                                                 mock_firestore_constructor,
                                                 mock_upload_with_retry,
                                                 mock_storage_client_constructor,
                                                 mocker: MockerFixture,
                                                 request):
        from agent_data_manager.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_doc_ref = mock_fs_instance.collection.return_value.document.return_value
        mock_storage_client_instance = mock_storage_client_constructor.return_value
        mock_bucket_instance = mock_storage_client_instance.bucket.return_value
        mock_blob_instance = mock_bucket_instance.blob.return_value
        mock_upload_with_retry.return_value = MagicMock()

        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        mock_os_remove.side_effect = OSError("Mocked os.remove failed")
        mock_log_warning = mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.logging.warning")

        input_data = {
            "index_name": "test_temp_delete_fail_index",
            "metadata_dict": {"doc1": {"text": "Successful run text"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(**input_data)
        print(f"\\nResult dictionary for {request.node.name}: {result}\\n")
        assert result is not None
        assert result.get("status") == "success"
"""

with open(file_path) as f:
    content = f.read()

# Regex: xóa toàn bộ class TestSaveMetadataToFaiss cũ và thay thế bằng block mới
new_content = re.sub(
    r"class TestSaveMetadataToFaiss:[\s\S]+?(?=\n\S|$)",
    replacement.strip(),
    content,
    flags=re.MULTILINE,
)

with open(file_path, "w") as f:
    f.write(new_content)
print(f"Đã thay thế toàn bộ class TestSaveMetadataToFaiss trong {file_path}")
