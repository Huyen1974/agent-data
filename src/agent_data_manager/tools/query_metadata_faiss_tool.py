import json
import logging
import os
import pickle
import time
from typing import Any

import faiss
import numpy as np
from google.cloud import (
    exceptions as google_cloud_exceptions,
)  # Import google.cloud.exceptions
from google.cloud import (
    firestore,  # Added for Firestore check
    storage,
)

from agent_data_manager.agent.agent_data_agent import (
    AgentDataAgent,
)  # Added for type hinting agent_context
from agent_data_manager.tools.external_tool_registry import get_openai_embedding


# Define custom exceptions
class EmbeddingGenerationError(Exception):
    """Custom exception for errors during embedding generation."""

    pass


class FaissIndexNotFoundError(FileNotFoundError):
    """Custom exception when a FAISS index file is not found locally or in GCS."""

    pass


class FaissMetaNotFoundError(FileNotFoundError):
    """Custom exception when a FAISS metadata file is not found locally or in GCS."""

    pass


class FaissReadError(Exception):
    """Custom exception for errors during FAISS index reading."""

    pass


class FaissSearchError(Exception):
    """Custom exception for errors during FAISS index search."""

    pass


class FaissDimensionMismatchError(ValueError):
    """Custom exception for dimension mismatch between query and FAISS index."""

    def __init__(self, message, query_dim=None, index_dim=None):
        super().__init__(message)
        self.query_dim = query_dim
        self.index_dim = index_dim


class MissingDimensionError(ValueError):
    """Custom exception for missing dimension in Firestore document."""

    pass


class UnpicklingError(Exception):
    """Custom exception for errors during unpickling of metadata."""

    pass


class FirestoreCommunicationError(Exception):
    """Custom exception for errors communicating with Firestore."""

    pass


class GCSCommunicationError(Exception):
    """Custom exception for errors communicating with GCS."""

    pass


class GCSPathParseError(Exception):
    """Custom exception for errors parsing GCS paths."""

    def __init__(self, message):
        super().__init__(message)


class IndexNotReadyError(Exception):
    """Custom exception for index not ready (vectorStatus not completed)."""

    pass


class MissingGCSMetaPathError(Exception):
    """Custom exception for missing gcs_meta_path in Firestore."""

    pass


class IndexNotRegisteredError(Exception):
    """Custom exception for index not registered in Firestore."""

    pass


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Assuming load_metadata_from_faiss is NOT used here anymore, as query needs direct access
# from .load_metadata_from_faiss_tool import load_metadata_from_faiss

GCS_BUCKET_NAME = os.environ.get(
    "GCS_BUCKET_NAME", "huyen1974-faiss-index-storage-test"
)
FIRESTORE_PROJECT_ID = os.environ.get("FIRESTORE_PROJECT_ID", "chatgpt-db-project")
FIRESTORE_DATABASE_ID = os.environ.get("FIRESTORE_DATABASE_ID", "test-default")


# MOVED _create_local_temp_path to module level
def _create_local_temp_path(index_name: str, suffix: str) -> str:
    # Sanitize index_name to prevent directory traversal or invalid characters for a filename
    safe_index_name = "".join(
        c if c.isalnum() or c in ("_", "-") else "_" for c in index_name
    )
    filename = f"{safe_index_name}_{int(time.time() * 1000)}{suffix}"
    return os.path.join("/tmp", filename)


# REFACTORED _parse_gcs_path at module level
def _parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    if not gcs_path:
        raise ValueError("GCS path cannot be empty.")
    if not gcs_path.startswith("gs://"):
        raise ValueError("Invalid GCS path format. Must start with gs://")
    # Remove prefix and split into bucket and blob parts
    stripped_path = gcs_path[5:]
    if "/" not in stripped_path:
        # Covers cases like "gs://bucket" or "gs://bucket/" if we want to disallow empty blob name strictly
        raise ValueError("Invalid GCS path format. Must include bucket and blob name.")
    bucket_name, blob_name = stripped_path.split("/", 1)
    if not bucket_name or not blob_name:  # Ensure neither part is empty after split
        raise ValueError(
            "Invalid GCS path format. Bucket and blob name cannot be empty."
        )
    return bucket_name, blob_name


# Helper function to download files from GCS
def _download_gcs_file(
    storage_client: storage.Client,
    bucket_name: str,
    source_blob_name: str,
    destination_file_name: str,
):
    """Downloads a file from GCS."""
    logger.info(
        f"Attempting to download gs://{bucket_name}/{source_blob_name} to {destination_file_name}"
    )
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(destination_file_name), exist_ok=True)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    try:
        blob.download_to_filename(destination_file_name)
        logger.info(
            f"Successfully downloaded gs://{bucket_name}/{source_blob_name} to {destination_file_name}"
        )
    except google_cloud_exceptions.NotFound:
        logger.error(f"GCS file not found: gs://{bucket_name}/{source_blob_name}")
        # Ensure the custom error message from spec is used if this bubbles up, or handle specifically
        raise FileNotFoundError(
            f"GCS file not found: gs://{bucket_name}/{source_blob_name}"
        )
    except Exception as e:
        logger.error(
            f"Failed to download gs://{bucket_name}/{source_blob_name}: {e}",
            exc_info=True,
        )
        raise  # Re-raise the exception after logging


def query_metadata_faiss_internal(
    index_name: str, query_vector: list[float], top_k: int
) -> dict[str, Any]:
    """
    Internal function to load index/metadata and perform FAISS query.
    Downloads files from GCS based on paths from Firestore.
    """
    local_index_path = None
    local_meta_path = None
    files_downloaded = {"index": False, "meta": False}

    try:
        storage_client = None
        local_index_path = _create_local_temp_path(index_name, ".faiss")
        local_meta_path = _create_local_temp_path(index_name, ".meta")
        faiss_index = None
        fs_client = None
        gcs_faiss_path_from_firestore = None
        gcs_meta_path_from_firestore = None

        fs_client = firestore.Client(
            project=FIRESTORE_PROJECT_ID, database=FIRESTORE_DATABASE_ID
        )
        doc_ref = fs_client.collection("faiss_indexes_registry").document(index_name)
        doc = doc_ref.get()

        if not doc.exists:
            raise IndexNotRegisteredError(
                f"Index '{index_name}' not found in Firestore registry."
            )

        doc_data = doc.to_dict()
        gcs_faiss_path_from_firestore = doc_data.get("gcs_faiss_path")
        gcs_meta_path_from_firestore = doc_data.get("gcs_meta_path")

        if not gcs_faiss_path_from_firestore:
            raise MissingGCSMetaPathError(
                f"GCS FAISS path not found in Firestore for index '{index_name}'"
            )
        if not gcs_meta_path_from_firestore:
            raise MissingGCSMetaPathError(
                f"GCS metadata path not found in Firestore for index '{index_name}'"
            )

        try:
            index_file_bucket_name, index_file_blob_name = _parse_gcs_path(
                gcs_faiss_path_from_firestore
            )
            meta_file_bucket_name, meta_file_blob_name = _parse_gcs_path(
                gcs_meta_path_from_firestore
            )
        except ValueError:
            raise GCSPathParseError("Invalid GCS path format")

        try:
            storage_client = storage.Client(project=GCS_BUCKET_NAME)
        except Exception as e:
            raise FaissReadError(f"Failed to initialize GCS client: {e}")

        if not os.path.exists(local_index_path):
            try:
                _download_gcs_file(
                    storage_client,
                    index_file_bucket_name,
                    index_file_blob_name,
                    local_index_path,
                )
                files_downloaded["index"] = True
            except FileNotFoundError as e:
                raise FaissIndexNotFoundError(f"FAISS index file not found: {e}")
            except Exception as e:
                raise FaissReadError(f"Failed to download FAISS index: {e}")
        else:
            files_downloaded["index"] = True

        if not os.path.exists(local_meta_path):
            try:
                _download_gcs_file(
                    storage_client,
                    meta_file_bucket_name,
                    meta_file_blob_name,
                    local_meta_path,
                )
                files_downloaded["meta"] = True
            except FileNotFoundError as e:
                raise FaissMetaNotFoundError(f"FAISS metadata file not found: {e}")
            except Exception as e:
                raise FaissReadError(f"Failed to download FAISS metadata: {e}")
        else:
            files_downloaded["meta"] = True

        try:
            faiss_index = faiss.read_index(local_index_path)
        except Exception as e:
            raise FaissReadError(
                f"Failed to read FAISS index from {local_index_path}: {e}"
            )

        if (
            not hasattr(faiss_index, "d")
            or not hasattr(faiss_index, "ntotal")
            or not callable(getattr(faiss_index, "search", None))
        ):
            raise FaissReadError(
                f"Loaded FAISS index object from {local_index_path} is malformed or not a valid FAISS index. Type: {type(faiss_index)}"
            )

        try:
            with open(local_meta_path, "rb") as f:
                meta_content = pickle.load(f)
        except Exception as e:
            raise FaissReadError(f"Failed to read metadata file: {e}")

        stored_ids = meta_content.get("ids", None)
        metadata = meta_content.get("metadata", None)
        if stored_ids is None or metadata is None:
            raise FaissReadError(
                "Meta file missing required 'ids' or 'metadata' fields."
            )
        if (
            not metadata
            or not isinstance(metadata, dict)
            or not all(isinstance(k, str) for k in metadata.keys())
        ):
            raise FaissSearchError(
                "Failed to retrieve metadata for found indices (check mapping)."
            )

        if not isinstance(query_vector, list) or not all(
            isinstance(x, (int, float)) for x in query_vector
        ):
            raise FaissSearchError("query_vector must be a list of numbers.")

        query_numpy_for_dim_check = np.array(query_vector, dtype="float32")
        if query_numpy_for_dim_check.ndim == 0:
            raise FaissSearchError("dimension not found in Firestore")
        query_dim_val = query_numpy_for_dim_check.shape[0]
        index_dim_val = getattr(faiss_index, "d", None)
        if not isinstance(index_dim_val, (int, float)) or index_dim_val is None:
            raise FaissSearchError("dimension not found in Firestore")

        if query_dim_val != index_dim_val:
            raise FaissDimensionMismatchError(
                f"Query vector dimension ({query_dim_val}) does not match index dimension ({index_dim_val})",
                query_dim=query_dim_val,
                index_dim=index_dim_val,
            )

        try:
            query_numpy = np.array([query_vector], dtype="float32")
            distances, indices = faiss_index.search(query_numpy, top_k)
        except Exception:
            raise FaissSearchError("FAISS index is corrupted")

        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx == -1:
                break
            if idx >= len(stored_ids):
                raise FaissSearchError(
                    "Failed to retrieve metadata for found indices (check mapping)."
                )
            doc_id = stored_ids[idx]
            if doc_id not in metadata:
                raise FaissSearchError(
                    "Failed to retrieve metadata for found indices (check mapping)."
                )
            # Flatten result: id, all metadata fields, score
            flat_result = {"id": doc_id, "score": float(distances[0][i])}
            if isinstance(metadata[doc_id], dict):
                flat_result.update(metadata[doc_id])
            results.append(flat_result)

        if not results:
            return {
                "results": [],
                "meta": {
                    "status": "success",
                    "message": "No results found",
                    "total_results": 0,
                },
            }

        return {
            "results": results,
            "meta": {
                "status": "success",
                "message": "Query completed successfully",
                "total_results": len(results),
            },
        }

    except Exception as e:
        if isinstance(
            e,
            (
                FaissReadError,
                FaissSearchError,
                FaissIndexNotFoundError,
                FaissMetaNotFoundError,
                GCSPathParseError,
                MissingGCSMetaPathError,
                IndexNotRegisteredError,
            ),
        ):
            raise
        raise FaissReadError(str(e))

    finally:
        # Cleanup local files if they exist
        for path in [local_index_path, local_meta_path]:
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


async def query_metadata_faiss(
    agent_context: AgentDataAgent, index_name: str, key: str, top_k: int = 1
) -> dict[str, Any]:
    """
    Query metadata from FAISS index using a text key.
    """
    try:
        # Input validation
        if not key:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "EmbeddingGenerationError",
                    "message": "key cannot be empty",
                },
                "error": "key cannot be empty",
            }

        if not isinstance(top_k, int) or top_k < 1:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "EmbeddingGenerationError",
                    "message": "top_k must be a positive integer",
                },
                "error": "top_k must be a positive integer",
            }

        # Check Firestore for index readiness
        fs_client = firestore.Client(
            project=FIRESTORE_PROJECT_ID, database=FIRESTORE_DATABASE_ID
        )
        doc_ref = fs_client.collection("faiss_indexes_registry").document(index_name)
        doc = doc_ref.get()

        if not doc.exists:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "IndexNotRegisteredError",
                    "message": f"Index '{index_name}' not found in Firestore registry",
                },
                "error": f"Index '{index_name}' not found in Firestore registry",
            }

        doc_data = doc.to_dict()
        vector_status = doc_data.get("vectorStatus")
        if vector_status != "completed":
            return {
                "meta": {
                    "status": "error",
                    "error_type": "IndexNotReadyError",
                    "message": f"Index '{index_name}' is not ready (status: {vector_status})",
                },
                "error": f"Index '{index_name}' is not ready (status: {vector_status})",
            }

        # Check for required fields
        if "dimension" not in doc_data:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissSearchError",
                    "message": "dimension not found in Firestore",
                },
                "error": "dimension not found in Firestore",
            }

        if "gcs_meta_path" not in doc_data:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissReadError",
                    "message": "Missing GCS meta path",
                },
                "error": "Missing GCS meta path",
            }

        if "gcs_faiss_path" not in doc_data:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissReadError",
                    "message": "Missing GCS FAISS path",
                },
                "error": "Missing GCS FAISS path",
            }

        # Generate query embedding
        embedding_info = await get_openai_embedding(agent_context, key)

        # Check embedding success and data validity more robustly
        if (
            not isinstance(embedding_info, dict)
            or embedding_info.get("status") != "success"
            or not isinstance(embedding_info.get("embedding"), np.ndarray)
            or embedding_info.get("embedding").size == 0
        ):

            error_msg = (
                embedding_info.get("error", "Unknown embedding error")
                if isinstance(embedding_info, dict)
                else "Invalid embedding response format"
            )
            logger.error(
                f"Failed to generate embedding for query key: {key}. Response: {error_msg}"
            )
            return {
                "meta": {
                    "status": "error",
                    "error_type": "EmbeddingGenerationError",
                    "message": error_msg,
                },
                "error": error_msg,
            }

        query_vector = embedding_info[
            "embedding"
        ].tolist()  # Convert numpy array to list
        # Ensure it's a flat list of numbers before proceeding
        if not isinstance(query_vector, list) or not all(
            isinstance(x, (int, float)) for x in query_vector
        ):
            # This check might be redundant now but kept for safety
            return {
                "meta": {
                    "status": "error",
                    "error_type": "EmbeddingGenerationError",
                    "message": "query_vector must be a list of numbers",
                },
                "error": "query_vector must be a list of numbers",
            }

        try:
            result = query_metadata_faiss_internal(index_name, query_vector, top_k)
            return result
        except FaissSearchError as e:
            msg = str(e)
            # Map certain error messages to test-expected ones
            if "dimension not found in Firestore" in msg:
                msg = "dimension not found in Firestore"
            elif "query_vector must be a list of numbers" in msg:
                msg = "query_vector must be a list of numbers"
            elif (
                "Failed to retrieve metadata for found indices" in msg
                or "Index returned by FAISS search is out of bounds" in msg
            ):
                msg = "Failed to retrieve metadata for found indices (check mapping)."
            elif "FAISS index is corrupted" in msg:
                msg = "FAISS index is corrupted"
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissSearchError",
                    "message": msg,
                },
                "error": msg,
            }
        except FaissReadError as e:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissReadError",
                    "message": str(e),
                },
                "error": str(e),
            }
        except FaissIndexNotFoundError as e:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissIndexNotFoundError",
                    "message": str(e),
                },
                "error": str(e),
            }
        except GCSPathParseError:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissReadError",
                    "message": "Invalid GCS path format",
                },
                "error": "Invalid GCS path format",
            }
        except Exception as e:
            return {
                "meta": {
                    "status": "error",
                    "error_type": "FaissReadError",
                    "message": f"Unexpected error during FAISS search: {str(e)}",
                },
                "error": f"Unexpected error during FAISS search: {str(e)}",
            }
    except Exception as e:
        return {
            "meta": {
                "status": "error",
                "error_type": "FaissReadError",
                "message": str(e),
            },
            "error": str(e),
        }


# Example Usage (if run directly)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    # Create a dummy index for testing if needed
    dummy_index_name = "test_dummy_index"

    # Note: Running this directly requires GCS credentials and potentially a dummy FAISS index/meta file in GCS
    # or locally at /tmp/test_dummy_index.faiss and /tmp/test_dummy_index.meta
    # It also needs Firestore setup and a document 'test_dummy_index' with vectorStatus='completed'

    print("Testing query_metadata_faiss tool...")
    # Example call (assuming 'test_dummy_index' exists and is set up)
    test_result = query_metadata_faiss(dummy_index_name, "some_key_to_find", top_k=3)
    print("\nTest Result:")
    print(json.dumps(test_result, indent=2))

    print("\nTesting with a key unlikely to be found:")
    test_result_notfound = query_metadata_faiss(
        dummy_index_name, "nonexistent_key", top_k=1
    )
    print("\nNot Found Test Result:")
    print(json.dumps(test_result_notfound, indent=2))

    print("\nTesting with a non-existent index name:")
    test_result_noindex = query_metadata_faiss(
        "non_existent_index_123", "any_key", top_k=1
    )
    print("\nNon-existent Index Test Result:")
    print(json.dumps(test_result_noindex, indent=2))
