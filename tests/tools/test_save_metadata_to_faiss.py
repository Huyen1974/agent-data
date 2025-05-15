import pytest
import faiss
import pickle
import logging
import os
import numpy as np
from unittest.mock import patch, MagicMock, call, PropertyMock, AsyncMock
import io
from google.cloud import exceptions as google_exceptions, storage
from google.api_core import exceptions as api_core_exceptions
from ADK.agent_data.tools.save_metadata_to_faiss_tool import EmbeddingGenerationError
import uuid

SAVE_TOOL_MODULE_PATH = "ADK.agent_data.tools.save_metadata_to_faiss_tool"
EXTERNAL_REGISTRY_MODULE_PATH = "ADK.agent_data.tools.external_tool_registry"

# Define the correct path for upload_with_retry from the utils module
UPLOAD_WITH_RETRY_PATH = f"{SAVE_TOOL_MODULE_PATH}.upload_with_retry"

GET_EMBEDDING_PATH = f"{EXTERNAL_REGISTRY_MODULE_PATH}.get_openai_embedding"
UPLOAD_GCS_SAVE_PATH = f"{SAVE_TOOL_MODULE_PATH}._upload_to_gcs"

# Path for patching google.cloud.storage.Client directly in the tool's module context
STORAGE_CLIENT_SAVE_PATH = f"{SAVE_TOOL_MODULE_PATH}.storage.Client"
FIRESTORE_CLIENT_PATH = f"{SAVE_TOOL_MODULE_PATH}.firestore.Client"

MOCKED_ENV_VARS = {
    "GCS_BUCKET_NAME": "huyen1974-faiss-index-storage-test",
    "FIRESTORE_PROJECT_ID": "chatgpt-db-project",
    "GOOGLE_CLOUD_PROJECT": "chatgpt-db-project",
    "FIRESTORE_DATABASE_ID": "test-default",
    "FAISS_INDEXES_COLLECTION": "faiss_indexes_registry",
    "OPENAI_API_KEY": "mock_api_key"
}

@pytest.fixture(autouse=True)
def mock_env_vars(mocker):
    # Clear os.environ and set it to our mocked values.
    mocker.patch.dict(os.environ, MOCKED_ENV_VARS, clear=True)

    # Define the mock getenv function that ONLY uses MOCKED_ENV_VARS
    def strict_mock_getenv(key, default=None):
        return MOCKED_ENV_VARS.get(key, default)

    # Patch os.getenv in the context of the module under test and globally.
    mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.os.getenv", side_effect=strict_mock_getenv)
    mocker.patch("os.getenv", side_effect=strict_mock_getenv)

    # Mock google.auth.default to control project ID detection by Google libraries
    # Attempt to patch it where it's most likely used by google-cloud-storage
    try:
        mock_google_auth_default = mocker.patch("google.auth.default")
        mock_credentials = MagicMock()
        # Set project_id on the mock_credentials if that's what the library checks
        # The actual attribute might vary (e.g., _project_id, project_id, etc.)
        # Forcing project_id on the credentials object directly and as a tuple return
        mock_credentials.project_id = "test-project" 
        mock_google_auth_default.return_value = (mock_credentials, "test-project")
    except ModuleNotFoundError:
        # If google.auth is not found at the top level (e.g. if not installed or test setup issues)
        # This is a fallback, ideally the patch above works.
        logging.warning("Could not patch google.auth.default, it might not be an issue if tests pass.")
    
    # Patch google.auth.default specifically in the tool's context if it imports it there
    try:
        # This assumes the tool might do: from google import auth; auth.default()
        # Or: import google.auth; google.auth.default()
        mock_tool_google_auth_default = mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.google.auth.default")
        tool_mock_credentials = MagicMock()
        tool_mock_credentials.project_id = "test-project"
        mock_tool_google_auth_default.return_value = (tool_mock_credentials, "test-project")
    except Exception: # Catch broader exceptions as patch can fail if module structure is not as assumed
        logging.warning(f"Could not patch {SAVE_TOOL_MODULE_PATH}.google.auth.default.")

@pytest.fixture(autouse=True)
def mock_logging(mocker):
    mocker.patch('logging.info')
    mocker.patch('logging.error')
    mocker.patch('logging.warning')

class TestSaveMetadataToFaiss:
    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_auto_embed(self,
                                   mock_get_embedding,
                                   mock_faiss_write_index,
                                   MockFaissIndexFlatL2,
                                   mock_pickle_dump,
                                   mocker, request):
        # Mock dependencies using mocker
        # Rely on the autouse mock_env_vars fixture for os.getenv
        # mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.os.getenv", 
        #              side_effect=lambda key, default=None: MOCKED_ENV_VARS.get(key, os.environ.get(key, default)))

        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH, return_value=MagicMock())
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss
        # Setup mock instances returned by constructors
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 2 # Ensure ntotal is set for vector_count check
        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}
        input_data = {
            "index_name": "test_index",
            "metadata_dict": {
                "doc1": {"text": "Hello world"},
                "doc2": {"text": "Another document"}
            },
            "text_field_to_embed": "text",
            "dimension": 10
        }
        expected_doc_ids_for_pickle = ['doc1', 'doc2']
        expected_metadata_for_pickle = input_data["metadata_dict"]
        expected_data_for_single_pickle_dump = {
            'ids': expected_doc_ids_for_pickle,
            'metadata': expected_metadata_for_pickle
        }
        result = await save_metadata_to_faiss(
            index_name=input_data["index_name"],
            metadata_dict=input_data["metadata_dict"],
            text_field_to_embed=input_data["text_field_to_embed"],
            dimension=input_data["dimension"]
        )
        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "success"
        assert "gcs_faiss_path" in result
        assert "gcs_meta_path" in result
        assert result.get("vector_count") == 2 # Check vector_count
        assert result.get("dimension") == 10
        assert result.get("index_name") == "test_index"
        # assert "index_type" in result # index_type might vary based on vector count
        assert "duration_seconds" in result
        assert result.get("gcs_upload_status") == "success" # Check GCS upload status
        MockFaissIndexFlatL2.assert_called_once_with(10)
        assert mock_index_instance.add.call_count == 1 # Should be 1 call for a batch
        mock_get_embedding.assert_has_calls([
            call(agent_context=None, text_to_embed="Hello world"),
            call(agent_context=None, text_to_embed="Another document")
        ], any_order=True)
        mock_faiss_write_index.assert_called_once_with(mock_index_instance, "/tmp/test_index.faiss")
        mock_pickle_dump.assert_called_once_with(expected_data_for_single_pickle_dump, mocker.ANY) # ANY for file obj
        mock_upload_with_retry_local.assert_has_calls([
            call(mock_blob, "/tmp/test_index.faiss"),
            call(mock_blob, "/tmp/test_index.meta")
        ], any_order=True)
        assert mock_upload_with_retry_local.call_count == 2
        mock_storage_client.assert_called_once_with(project="chatgpt-db-project")
        mock_actual_storage_client_instance.bucket.assert_called_once_with(MOCKED_ENV_VARS["GCS_BUCKET_NAME"])
        mock_bucket.blob.assert_has_calls([
            call("test_index.faiss"),
            call("test_index.meta")
        ], any_order=True)
        assert mock_bucket.blob.call_count == 2
        mock_firestore_constructor.assert_called()
        mock_doc_ref.set.assert_called()
        actual_set_call_args = mock_doc_ref.set.call_args[0][0]
        assert actual_set_call_args.get("vectorStatus") == "completed"
    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    async def test_save_with_vector_data(self,
                                         MockFaissIndexFlatL2,
                                         mock_faiss_write_index,
                                         mock_pickle_dump,
                                         mocker, request):
        # Mock dependencies using mocker
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        # Simulate GCS upload failure for this test case
        mock_upload_with_retry_local.side_effect = google_exceptions.NotFound("Mocked GCS upload failed for vector data test")
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss
        # Setup mock instances
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mocker.patch.object(mock_index_instance, 'ntotal', new=2) # Ensure ntotal is set
        input_data = {
            "index_name": "test_index_vector",
            "metadata_dict": {
                "doc1": {"text": "Hello world"},
                "doc2": {"text": "Another document"}
            },
            "vector_data": [
                [0.1]*10, # Corresponds to doc1
                [0.2]*10  # Corresponds to doc2
            ],
            "dimension": 10
        }
        expected_doc_ids_for_pickle = ['doc1', 'doc2']
        expected_metadata_for_pickle = input_data["metadata_dict"]
        expected_data_for_single_pickle_dump = {
            'ids': expected_doc_ids_for_pickle,
            'metadata': expected_metadata_for_pickle
        }
        result = await save_metadata_to_faiss(
            index_name=input_data["index_name"],
            metadata_dict=input_data["metadata_dict"],
            vector_data=input_data["vector_data"],
            dimension=input_data["dimension"]
        )
        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert isinstance(result, dict)
        # This test should now expect an error due to GCS upload failure
        assert result["status"] == "error"
        MockFaissIndexFlatL2.assert_called_once_with(10)
        mock_index_instance.add.assert_called_once()
        added_vectors = mock_index_instance.add.call_args[0][0]
        expected_np_vectors = np.array([[0.1]*10, [0.2]*10], dtype=np.float32)
        assert np.array_equal(added_vectors, expected_np_vectors)
        mock_faiss_write_index.assert_called_once_with(mock_index_instance, "/tmp/test_index_vector.faiss")
        mock_pickle_dump.assert_called_once_with(expected_data_for_single_pickle_dump, mocker.ANY)
        # Assert that upload was attempted, even if it fails
        mock_upload_with_retry_local.assert_called()
        mock_storage_client.assert_called_once_with(project="chatgpt-db-project")
        mock_actual_storage_client_instance.bucket.assert_called_once_with(MOCKED_ENV_VARS["GCS_BUCKET_NAME"])
        mock_bucket.blob.assert_has_calls([
            call("test_index_vector.faiss"),
            call("test_index_vector.meta")
        ], any_order=True)
        assert mock_bucket.blob.call_count == 2
        mock_firestore_constructor.assert_called()
        # Firestore doc should not be set if GCS upload fails
        mock_doc_ref.set.assert_not_called()
        assert result.get("dimension") == 10

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    async def test_save_openai_embedding_error(self,
                                               MockFaissIndexFlatL2,
                                               mock_get_embedding,
                                               mock_faiss_write_index,
                                               mock_pickle_dump,
                                               mocker, request):
        # Mock dependencies using mocker
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH, return_value=MagicMock())
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss, EmbeddingGenerationError
        # Setup mock instances
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 1 # For one successful embedding
        mock_get_embedding.side_effect = [
            {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}, # doc1 succeeds
            EmbeddingGenerationError("Simulated embedding error for doc2") # doc2 fails
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
        result = await save_metadata_to_faiss(
            index_name=input_data["index_name"],
            metadata_dict=input_data["metadata_dict"],
            text_field_to_embed=input_data["text_field_to_embed"],
            dimension=input_data["dimension"]
        )
        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "success" # WAS "error"
        # Only check meta and embedding error details if meta exists
        if "meta" in result:
            assert "embedding_generation_errors" in result["meta"]
            assert "doc2" in result["meta"]["embedding_generation_errors"]
            assert "Simulated embedding error for doc2" in result["meta"]["embedding_generation_errors"]["doc2"]
            assert "doc2" in result.get("meta", {}).get("failed_doc_ids", [])
            assert result.get("meta", {}).get("embedded_docs_count") == 1 # Only doc1 was embedded
        # Always check main success fields
        assert result.get("index_name") == input_data["index_name"]
        assert result.get("vector_count") == 1
        assert result.get("dimension") == 10
        assert result.get("gcs_upload_status") == "success"
        assert result.get("firestore_update_status") == "success"

        mock_get_embedding.assert_any_call(agent_context=None, text_to_embed="Text that will succeed")
        mock_get_embedding.assert_any_call(agent_context=None, text_to_embed="Text that will cause embedding error")
        
        MockFaissIndexFlatL2.assert_called_once_with(10) # Index created
        mock_index_instance.add.assert_called_once() # doc1's vector added
        mock_faiss_write_index.assert_called_once() # Index for doc1 written
        mock_pickle_dump.assert_called_once() # Meta for doc1 dumped
        mock_upload_with_retry_local.assert_called() # Upload for doc1 attempted
        mock_firestore_constructor.assert_called()
        mock_doc_ref.set.assert_called()

        mock_storage_client.assert_called_once_with(project="chatgpt-db-project")

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_gcs_upload_faiss_fails(self,
                                               mock_get_embedding,
                                               mock_faiss_write_index,
                                               mock_pickle_dump,
                                               mocker, request):
        # Mock dependencies using mocker
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        # Define a side_effect function that will raise an error for any upload attempt
        def gcs_upload_failure_side_effect(*args, **kwargs):
            raise google_exceptions.NotFound("Mocked GCS upload failed")
        mock_upload_with_retry_local.side_effect = gcs_upload_failure_side_effect
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss
        # Setup mock instances
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        MockFaissIndexFlatL2 = mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 1 # One document is processed
        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}
        
        def upload_side_effect(blob, source_file_name):
            if source_file_name.endswith(".faiss"):
                raise google_exceptions.NotFound("Mocked GCS FAISS upload failed")
            elif source_file_name.endswith(".meta"):
                return None 
            raise ValueError(f"Unexpected upload call: {source_file_name}")
            
        mock_upload_with_retry_local.side_effect = upload_side_effect

        input_data = {
            "index_name": "test_index_gcs_upload_fails",
            "metadata_dict": {
                "doc1": {"text": "Hello world"},
            },
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(
            index_name=input_data["index_name"],
            metadata_dict=input_data["metadata_dict"],
            text_field_to_embed=input_data["text_field_to_embed"],
            dimension=input_data["dimension"]
        )
        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert isinstance(result, dict)
        assert result.get("status") == "error" 
        # The tool structure for GCS error returns error in "message" and "meta.error_type"
        assert "message" in result 
        assert "Mocked GCS FAISS upload failed" in result["message"]
        assert result.get("meta", {}).get("error_type") == "GCSCommunicationError" 
        assert result.get("gcs_upload_status") == "failed"

        mock_storage_client.assert_called_once_with(project="chatgpt-db-project")
        
        mock_upload_with_retry_local.assert_any_call(mock_blob, "/tmp/test_index_gcs_upload_fails.faiss")
        mock_firestore_constructor.assert_called()
        mock_doc_ref.set.assert_not_called() 

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_gcs_upload_meta_fails(self,
                                              mock_get_embedding,
                                              mock_faiss_write_index,
                                              mock_pickle_dump,
                                              mocker, request):
        # Mock dependencies using mocker
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss
        # Setup mock instances
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        MockFaissIndexFlatL2 = mocker.patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 1 # One document is processed
        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}
        
        def upload_side_effect_meta_fail(blob, source_file_name):
            if source_file_name.endswith(".meta"):
                raise google_exceptions.NotFound("Mocked GCS META upload failed")
            elif source_file_name.endswith(".faiss"):
                return None 
            raise ValueError(f"Unexpected upload call: {source_file_name}")
            
        mock_upload_with_retry_local.side_effect = upload_side_effect_meta_fail

        input_data = {
            "index_name": "test_index_gcs_meta_upload_fails",
            "metadata_dict": {
                "doc1": {"text": "Hello world for meta fail"},
            },
            "text_field_to_embed": "text",
            "dimension": 10
        }
        result = await save_metadata_to_faiss(
            index_name=input_data["index_name"],
            metadata_dict=input_data["metadata_dict"],
            text_field_to_embed=input_data["text_field_to_embed"],
            dimension=input_data["dimension"]
        )
        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "error" 
        assert "message" in result 
        assert "Mocked GCS META upload failed" in result["message"]
        assert result.get("meta", {}).get("error_type") == "GCSCommunicationError" 
        assert result.get("gcs_upload_status") == "failed"

        mock_storage_client.assert_called_once_with(project="chatgpt-db-project")
        
        # Both .faiss and .meta upload should be attempted
        mock_upload_with_retry_local.assert_any_call(mock_blob, "/tmp/test_index_gcs_meta_upload_fails.faiss")
        mock_upload_with_retry_local.assert_any_call(mock_blob, "/tmp/test_index_gcs_meta_upload_fails.meta")
        assert mock_upload_with_retry_local.call_count == 2

        # Firestore should not be updated if GCS upload fails
        mock_firestore_constructor.assert_called() # Client might be initialized
        mock_doc_ref.set.assert_not_called() 

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_firestore_update_fails(self,
                                               mock_get_embedding,
                                               mock_faiss_write_index,
                                               MockFaissIndexFlatL2,
                                               mock_pickle_dump,
                                               mocker, request):
        # Mock dependencies
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH, return_value=MagicMock()) # GCS succeeds
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss
        
        # Setup mock instances
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value
        # Simulate Firestore .set() failure
        mock_doc_ref.set.side_effect = api_core_exceptions.Aborted("Mocked Firestore update failed")

        mock_actual_storage_client_instance = MagicMock(spec=storage.Client)
        mock_storage_client.return_value = mock_actual_storage_client_instance
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_actual_storage_client_instance.bucket = MagicMock()
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 1
        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        input_data = {
            "index_name": "test_firestore_fail_index",
            "metadata_dict": {"doc1": {"text": "Firestore test text"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }

        result = await save_metadata_to_faiss(**input_data)
        
        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "partial_success" # Corrected status
        assert "message" in result
        assert "FAISS/GCS successful, but Firestore update failed" in result["message"] # Corrected message
        assert result.get("meta", {}).get("error_type") == "FirestoreRegistryError"
        assert result.get("firestore_update_status") == "failed"
        assert result.get("gcs_upload_status") == "success" # GCS part should succeed

        # Verify mocks
        MockFaissIndexFlatL2.assert_called_once_with(10)
        mock_index_instance.add.assert_called_once()
        mock_faiss_write_index.assert_called_once()
        mock_pickle_dump.assert_called_once()
        
        assert mock_upload_with_retry_local.call_count == 2 # Both .faiss and .meta attempted and succeeded
        mock_storage_client.assert_called_once_with(project=MOCKED_ENV_VARS["GOOGLE_CLOUD_PROJECT"])
        mock_actual_storage_client_instance.bucket.assert_called_once_with(MOCKED_ENV_VARS["GCS_BUCKET_NAME"])
        assert mock_bucket.blob.call_count == 2
        
        mock_firestore_constructor.assert_called_once()
        mock_fs_instance.collection.assert_called_once_with(MOCKED_ENV_VARS["FAISS_INDEXES_COLLECTION"])
        mock_collection_ref.document.assert_called_once_with("test_firestore_fail_index")
        mock_doc_ref.set.assert_called_once() # Attempt to set was made

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock()) # Not used, but keep pattern
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_empty_metadata_dict(self,
                                            mock_get_embedding,
                                            mock_faiss_write_index,
                                            MockFaissIndexFlatL2,
                                            mock_pickle_dump,
                                            mocker, request):
        # Mock dependencies that might be called even with empty input
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        input_data = {
            "index_name": "test_empty_meta_index",
            "metadata_dict": {},
            "text_field_to_embed": "text", # Still need this if auto-embedding path is taken
            "dimension": 10
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "error" # Changed from "success"
        assert "No valid texts found for embedding" in result.get("message") # More specific check
        assert result.get("meta", {}).get("embedded_docs_count") == 0 # Check in meta
        assert result.get("index_name") is None # index_name is also in meta for this error
        assert result.get("meta", {}).get("index_name") == "test_empty_meta_index"
        assert result.get("gcs_faiss_path") is None
        assert result.get("gcs_meta_path") is None
        # For early ValueError, gcs_upload_status and firestore_update_status are not set
        # assert result.get("gcs_upload_status") == "skipped"
        # assert result.get("firestore_update_status") == "skipped"
        assert result.get("meta", {}).get("error_type") == "ValueError"
        
        # Ensure no core processing or I/O operations were performed
        mock_get_embedding.assert_not_called()
        MockFaissIndexFlatL2.assert_not_called()
        mock_faiss_write_index.assert_not_called()
        mock_pickle_dump.assert_not_called()
        mock_upload_with_retry_local.assert_not_called()
        
        # Firestore client might be initialized but no document set/update should occur for an empty index
        mock_firestore_constructor.assert_called_once()
        mock_fs_instance = mock_firestore_constructor.return_value
        mock_fs_instance.collection.assert_not_called() # collection should not be called for empty metadata
        mock_doc_ref = mock_fs_instance.collection.return_value.document.return_value
        mock_doc_ref.set.assert_not_called() 

        mock_storage_client.assert_not_called() # If no files, no client needed for bucket/blob ops

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_text_field_missing_in_metadata(self,
                                                       mock_get_embedding,
                                                       mock_faiss_write_index,
                                                       MockFaissIndexFlatL2,
                                                       mock_pickle_dump,
                                                       mocker, request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH, return_value=MagicMock())
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value

        # Corrected storage client and bucket mocking
        mock_storage_client_constructor = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        mock_actual_storage_client_instance = mock_storage_client_constructor.return_value
        
        mock_bucket_instance = MagicMock(spec=storage.Bucket)
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket_instance
        
        mock_blob_instance = MagicMock(spec=storage.Blob)
        mock_bucket_instance.blob.return_value = mock_blob_instance

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 2 # Expecting two docs to be embedded (doc1, doc3)
        # doc1 will be embedded, doc2 will be skipped (missing text_field), doc3 will be embedded
        mock_get_embedding.side_effect = [
            {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}, # for doc1
            {"embedding": np.array([0.3]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}  # for doc3
        ]

        input_metadata = {
            "doc1": {"text": "This is doc1"},
            "doc2": {"other_field": "This is doc2, missing text field"},
            "doc3": {"text": "This is doc3"}
        }
        input_data = {
            "index_name": "test_text_field_missing_index",
            "metadata_dict": input_metadata,
            "text_field_to_embed": "text",
            "dimension": 10
        }
        
        expected_doc_ids_for_pickle = ['doc1', 'doc3']
        expected_metadata_for_pickle = {
            "doc1": input_metadata["doc1"],
            "doc3": input_metadata["doc3"]
        }
        expected_data_for_pickle = {
            'ids': expected_doc_ids_for_pickle,
            'metadata': expected_metadata_for_pickle
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "success"
        assert result.get("vector_count") == 2
        assert result.get("dimension") == 10
        assert result.get("index_name") == "test_text_field_missing_index"
        assert result.get("gcs_upload_status") == "success"
        assert result.get("firestore_update_status") == "success"

        mock_get_embedding.assert_has_calls([
            call(agent_context=None, text_to_embed="This is doc1"),
            call(agent_context=None, text_to_embed="This is doc3")
        ], any_order=True)
        assert mock_get_embedding.call_count == 2
        
        MockFaissIndexFlatL2.assert_called_once_with(10)
        assert mock_index_instance.add.call_count == 1 # Batch add for 2 vectors
        added_vectors = mock_index_instance.add.call_args[0][0]
        assert added_vectors.shape[0] == 2 # Two vectors added

        mock_faiss_write_index.assert_called_once()
        mock_pickle_dump.assert_called_once_with(expected_data_for_pickle, mocker.ANY)
        assert mock_upload_with_retry_local.call_count == 2
        
        # Verify storage client calls
        mock_storage_client_constructor.assert_called_once_with(project=MOCKED_ENV_VARS["GOOGLE_CLOUD_PROJECT"])
        mock_actual_storage_client_instance.bucket.assert_called_once_with(MOCKED_ENV_VARS["GCS_BUCKET_NAME"])
        assert mock_bucket_instance.blob.call_count == 2
        mock_bucket_instance.blob.assert_has_calls([
            call(f"{input_data['index_name']}.faiss"),
            call(f"{input_data['index_name']}.meta")
        ], any_order=True)

        mock_doc_ref.set.assert_called_once()

    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    async def test_save_dimension_mismatch_with_vector_data(self,
                                                            mock_faiss_write_index,
                                                            MockFaissIndexFlatL2,
                                                            mock_pickle_dump,
                                                            mocker, request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_doc_ref = mock_fs_instance.collection.return_value.document.return_value

        input_data = {
            "index_name": "test_dim_mismatch_index",
            "metadata_dict": {
                "doc1": {"description": "Vector with 5 dims"}
            },
            "vector_data": [
                [0.1, 0.2, 0.3, 0.4, 0.5] # 5 dimensions
            ],
            "dimension": 10 # Expecting 10 dimensions
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "message" in result
        assert result["message"] == "Provided dimension 10 does not match vector dimension 5."
        assert result.get("meta", {}).get("error_type") == "InvalidVectorDataError"
        assert result.get("index_name") is None 
        assert result.get("meta", {}).get("index_name") == "test_dim_mismatch_index"

        # Ensure no core processing or I/O happened due to early validation failure
        MockFaissIndexFlatL2.assert_not_called()
        mock_faiss_write_index.assert_not_called()
        mock_pickle_dump.assert_not_called()
        mock_upload_with_retry_local.assert_not_called()
        mock_storage_client.assert_not_called() # Should not be called if no files to upload
        
        mock_firestore_constructor.assert_called_once() # Client might be initialized as part of setup
        mock_doc_ref.set.assert_not_called() # No Firestore update on validation error

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_all_embeddings_fail(self,
                                            mock_get_embedding,
                                            mock_faiss_write_index,
                                            MockFaissIndexFlatL2,
                                            mock_pickle_dump,
                                            mocker, request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        mock_storage_client = mocker.patch(STORAGE_CLIENT_SAVE_PATH)

        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss, EmbeddingGenerationError

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_collection_ref = mock_fs_instance.collection.return_value
        mock_doc_ref = mock_collection_ref.document.return_value
        
        # Simulate embedding failure for all documents
        mock_get_embedding.side_effect = EmbeddingGenerationError("Simulated global embedding API error")

        input_metadata = {
            "doc1": {"text": "Text for doc1"},
            "doc2": {"text": "Text for doc2"}
        }
        input_data = {
            "index_name": "test_all_embed_fail_index",
            "metadata_dict": input_metadata,
            "text_field_to_embed": "text",
            "dimension": 10
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        # The overall status should still be 'success' as the tool attempts to save what it can (which is nothing here)
        # but it should report that no vectors were generated/saved.
        assert result.get("status") == "error" # Changed from "success"
        assert "No embeddings could be successfully processed" in result.get("message") # Check actual message
        assert result.get("meta", {}).get("embedded_docs_count") == 0 # Check in meta
        # assert result.get("dimension") == 10 # Dimension is from input; not present in current error output
        assert result.get("index_name") is None # index_name is also in meta for this error
        assert result.get("meta", {}).get("index_name") == "test_all_embed_fail_index"
        
        assert "meta" in result
        assert "embedding_generation_errors" in result["meta"]
        assert "doc1" in result["meta"]["embedding_generation_errors"]
        assert "doc2" in result["meta"]["embedding_generation_errors"]
        assert "Simulated global embedding API error" in result["meta"]["embedding_generation_errors"]["doc1"]
        assert "Simulated global embedding API error" in result["meta"]["embedding_generation_errors"]["doc2"]
        assert set(result.get("meta", {}).get("failed_doc_ids", [])) == {"doc1", "doc2"} # Use set comparison for order-insensitivity
        assert result.get("meta", {}).get("error_type") == "EmbeddingGenerationError" # From log
        
        assert result.get("gcs_faiss_path") is None
        assert result.get("gcs_meta_path") is None
        # For this error path, gcs_upload_status and firestore_update_status are not set
        # assert result.get("gcs_upload_status") == "skipped" 
        # assert result.get("firestore_update_status") == "skipped"

        mock_get_embedding.assert_has_calls([
            call(agent_context=None, text_to_embed="Text for doc1"),
            call(agent_context=None, text_to_embed="Text for doc2")
        ], any_order=True)
        assert mock_get_embedding.call_count == 2

        MockFaissIndexFlatL2.assert_not_called() # No index if no vectors
        mock_faiss_write_index.assert_not_called()
        mock_pickle_dump.assert_not_called()
        mock_upload_with_retry_local.assert_not_called()
        mock_storage_client.assert_not_called()

        # Firestore client might be init, but no actual doc set for an empty/failed index processing
        mock_firestore_constructor.assert_called_once()
        mock_fs_instance = mock_firestore_constructor.return_value # Get the instance for further assertions
        mock_fs_instance.collection.assert_not_called() # collection() should not be called
        mock_doc_ref = mock_collection_ref.document.return_value # mock_collection_ref itself is not called
        mock_doc_ref.set.assert_not_called()

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_faiss_write_index_fails(self,
                                                mock_get_embedding,
                                                mock_faiss_write_index,
                                                MockFaissIndexFlatL2,
                                                mock_pickle_dump, 
                                                mocker, request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        # Corrected GCS mocking:
        mock_storage_client_constructor = mocker.patch(STORAGE_CLIENT_SAVE_PATH)
        mock_actual_storage_client_instance = mock_storage_client_constructor.return_value
        mock_bucket_instance = MagicMock(spec=storage.Bucket)
        mock_actual_storage_client_instance.bucket.return_value = mock_bucket_instance
        mock_blob_instance_meta = MagicMock(spec=storage.Blob) # For .meta file
        # Make blob return the specific blob instance depending on the call (if needed, or a default one)
        mock_bucket_instance.blob.return_value = mock_blob_instance_meta


        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_doc_ref = mock_fs_instance.collection.return_value.document.return_value

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 1
        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        mock_faiss_write_index.side_effect = OSError("Mocked FAISS write_index failed")

        input_data = {
            "index_name": "test_faiss_write_fail_index",
            "metadata_dict": {"doc1": {"text": "FAISS write test"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }
        
        expected_doc_ids_for_pickle = ['doc1']
        expected_metadata_for_pickle = input_data["metadata_dict"]
        expected_data_for_pickle = {
            'ids': expected_doc_ids_for_pickle,
            'metadata': expected_metadata_for_pickle
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "message" in result
        assert "Failed to save FAISS index to local disk" in result["message"]
        assert "Mocked FAISS write_index failed" in result["message"]
        assert result.get("meta", {}).get("error_type") == "LocalFAISSError"
        assert result.get("index_name") == "test_faiss_write_fail_index"
        assert result.get("vector_count") == 1 
        assert result.get("gcs_faiss_path") is None 
        
        MockFaissIndexFlatL2.assert_called_once_with(10)
        mock_index_instance.add.assert_called_once()
        mock_faiss_write_index.assert_called_once_with(mock_index_instance, "/tmp/test_faiss_write_fail_index.faiss")
        
        mock_pickle_dump.assert_called_once_with(expected_data_for_pickle, mocker.ANY)
        
        upload_calls = mock_upload_with_retry_local.call_args_list
        assert len(upload_calls) == 1
        assert upload_calls[0][0][0] == mock_blob_instance_meta 
        assert upload_calls[0][0][1].endswith(".meta") 
        
        mock_storage_client_constructor.assert_called_once_with(project=MOCKED_ENV_VARS["GOOGLE_CLOUD_PROJECT"])
        mock_actual_storage_client_instance.bucket.assert_called_once_with(MOCKED_ENV_VARS["GCS_BUCKET_NAME"])
        mock_bucket_instance.blob.assert_called_once_with(f"{input_data['index_name']}.meta")

        mock_firestore_constructor.assert_called_once()
        mock_doc_ref.set.assert_not_called()

    @patch(f"{SAVE_TOOL_MODULE_PATH}.openai_client", MagicMock())
    @patch(f"{SAVE_TOOL_MODULE_PATH}.pickle.dump")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.IndexFlatL2")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.faiss.write_index")
    @patch(f"{SAVE_TOOL_MODULE_PATH}.get_openai_embedding", new_callable=AsyncMock)
    async def test_save_pickle_dump_fails(self,
                                          mock_get_embedding,
                                          mock_faiss_write_index,
                                          MockFaissIndexFlatL2,
                                          mock_pickle_dump,
                                          mocker, request):
        mock_firestore_constructor = mocker.patch(FIRESTORE_CLIENT_PATH)
        mock_upload_with_retry_local = mocker.patch(UPLOAD_WITH_RETRY_PATH)
        
        # Patch storage.Client constructor
        mock_gcs_client_constructor = mocker.patch(STORAGE_CLIENT_SAVE_PATH) 
        mock_gcs_client_instance = MagicMock(spec=storage.Client) # Instance if constructor is called
        mock_gcs_client_constructor.return_value = mock_gcs_client_instance
        
        # Explicitly mock the .bucket attribute/method on the instance
        mock_gcs_client_instance.bucket = MagicMock() # Assign a mock to the 'bucket' method name
        mock_bucket_return = MagicMock(spec=storage.Bucket) # This is what the .bucket() mock will return
        mock_gcs_client_instance.bucket.return_value = mock_bucket_return
        
        mock_blob_return = MagicMock(spec=storage.Blob) # This is what bucket_instance.blob() will return
        mock_bucket_return.blob.return_value = mock_blob_return
    
        from ADK.agent_data.tools.save_metadata_to_faiss_tool import save_metadata_to_faiss

        mock_fs_instance = mock_firestore_constructor.return_value
        mock_doc_ref = mock_fs_instance.collection.return_value.document.return_value

        mock_index_instance = MockFaissIndexFlatL2.return_value
        mock_index_instance.ntotal = 1
        mock_get_embedding.return_value = {"embedding": np.array([0.1]*10, dtype=np.float32), "total_tokens": 5, "status": "success"}

        mock_pickle_dump.side_effect = pickle.PicklingError("Mocked pickle.dump failed")

        input_data = {
            "index_name": "test_pickle_dump_fail_index",
            "metadata_dict": {"doc1": {"text": "Pickle dump test"}},
            "text_field_to_embed": "text",
            "dimension": 10
        }

        result = await save_metadata_to_faiss(**input_data)

        print(f"\nResult dictionary for {request.node.name}: {result}\n")
        assert result is not None
        assert result.get("status") == "error"
        assert "message" in result
        assert result["message"] == "Mocked pickle.dump failed"
        assert result.get("meta", {}).get("error_type") == "PicklingError"
        assert result.get("index_name") is None
        assert result.get("meta", {}).get("index_name") == "test_pickle_dump_fail_index"
        
        MockFaissIndexFlatL2.assert_called_once_with(10)
        mock_index_instance.add.assert_called_once()
        mock_faiss_write_index.assert_called_once()
        mock_pickle_dump.assert_called_once()
    
        # For this error path (pickle dump fail), no bucket/blob ops should happen as upload is skipped
        mock_gcs_client_instance.bucket.assert_not_called()
        mock_bucket_return.blob.assert_not_called()

        mock_firestore_constructor.assert_called_once()
        mock_doc_ref.set.assert_not_called()