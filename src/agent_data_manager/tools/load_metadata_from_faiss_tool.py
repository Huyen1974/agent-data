import os
import pickle
import logging  # Added logging

# import faiss # No longer needed if index isn't loaded/downloaded
from google.cloud import storage
from google.cloud import exceptions as google_cloud_exceptions  # Import google.cloud.exceptions
import time
from google.cloud import firestore  # Added for Firestore check

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

GCS_BUCKET_NAME = "huyen1974-faiss-index-storage-test"  # Defined bucket name
# FAISS_DIR = "ADK/agent_data/faiss_indices"
FIRESTORE_PROJECT_ID = os.environ.get(
    "FIRESTORE_PROJECT_ID", "chatgpt-db-project"
)  # Ensure FIRESTORE_PROJECT_ID is used


def _parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """Parses a GCS path (gs://bucket/blob) into bucket name and blob name."""
    if not gcs_path.startswith("gs://"):
        raise ValueError("Invalid GCS path format. Must start with gs://")
    path_parts = gcs_path[5:].split("/", 1)
    if len(path_parts) < 2:
        raise ValueError("Invalid GCS path format. Must include bucket and blob name.")
    return path_parts[0], path_parts[1]


def _download_gcs_file(storage_client, bucket_name, source_blob_name, destination_file_name):
    """Downloads a file from GCS. Raises Exception on failure."""
    logger.info(f"Attempting to download gs://{bucket_name}/{source_blob_name} to {destination_file_name}")
    # storage_client = storage.Client() # Client should be initialized once per function call if needed
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    # Add retry or check blob.exists() before download?
    blob.download_to_filename(destination_file_name)
    logger.info(f"Downloaded GCS file gs://{bucket_name}/{source_blob_name} to {destination_file_name}")


async def load_metadata_from_faiss(index_name: str):
    """
    Loads metadata from a .meta file associated with a FAISS index.
    Downloads ONLY the .meta file from GCS if local file not found.
    Cleans up the temporary local .meta file.

    Args:
        index_name (str): The name of the FAISS index (used to find .meta file).

    Returns:
        dict: The loaded metadata dictionary or an error dictionary.
    """
    start_time = time.time()
    storage_client = None
    gcs_meta_path_from_firestore = None  # Variable to store GCS path from Firestore

    # --- Start Firestore Status Check ---
    try:
        logger.info(f"Checking Firestore status for index: {index_name} in collection 'faiss_indexes_registry'")
        # Use FIRESTORE_PROJECT_ID from env var
        fs_client = firestore.Client(project=FIRESTORE_PROJECT_ID, database="test-default")
        # Query 'faiss_indexes_registry' collection
        doc_ref = fs_client.collection("faiss_indexes_registry").document(index_name)
        doc = doc_ref.get()

        if not doc.exists:
            logger.warning(f"Index '{index_name}' not found in Firestore registry.")
            # Specific error message format
            return {
                "error": f"Index '{index_name}' not found in Firestore registry.",
                "meta": {
                    "status": "error",
                    "execution_time": time.time() - start_time,
                    "error_type": "IndexNotRegisteredError",
                },
            }

        doc_data = doc.to_dict()
        vector_status = doc_data.get("vectorStatus")
        gcs_meta_path_from_firestore = doc_data.get("gcs_meta_path")  # Get gcs_meta_path

        logger.info(
            f"Firestore data for '{index_name}': vectorStatus={vector_status}, gcs_meta_path={gcs_meta_path_from_firestore}"
        )

        if vector_status != "completed":
            logger.warning(f"Index '{index_name}' vectorStatus is '{vector_status}', not 'completed'.")
            # Specific error message format
            return {
                "error": f"Index '{index_name}' is not ready (vectorStatus: {vector_status}).",
                "meta": {
                    "status": "error",
                    "execution_time": time.time() - start_time,
                    "error_type": "IndexNotReadyError",
                },
            }

        if not gcs_meta_path_from_firestore:
            logger.error(f"gcs_meta_path not found in Firestore document for index '{index_name}'.")
            return {
                "error": f"gcs_meta_path not found in Firestore for index '{index_name}'.",
                "meta": {
                    "status": "error",
                    "execution_time": time.time() - start_time,
                    "error_type": "MissingGCSMetaPathError",
                },
            }

        logger.info(
            f"Firestore status check passed for index '{index_name}'. Using gcs_meta_path: {gcs_meta_path_from_firestore}"
        )

    except Exception as fs_e:
        logger.error(f"Failed to check Firestore status for index '{index_name}': {fs_e}", exc_info=True)
        return {
            # Keep a generic error for unexpected Firestore issues but provide details
            "error": f"Failed to check Firestore status for index '{index_name}': {str(fs_e)}",
            "meta": {
                "status": "error",
                "execution_time": time.time() - start_time,
                "error_type": "FirestoreCheckFailed",
            },
        }
    # --- End Firestore Status Check ---

    # Define local path for the .meta file
    # The local filename can be derived from the index_name or gcs_meta_path for uniqueness if needed
    local_meta_filename = f"{index_name}.meta"  # Or parse from gcs_meta_path_from_firestore
    meta_path = f"/tmp/{local_meta_filename}"
    file_downloaded = False

    try:
        # Download using gcs_meta_path from Firestore
        logger.info(f"Attempting GCS download using path from Firestore: {gcs_meta_path_from_firestore}")
        try:
            storage_client = storage.Client()  # Initialize client if not already

            # Parse bucket and blob name from gcs_meta_path_from_firestore
            bucket_name, meta_blob_name = _parse_gcs_path(gcs_meta_path_from_firestore)

            # Check if local file exists (e.g. from a previous failed run, though unlikely with /tmp)
            # This check might be redundant if always downloading to a fresh /tmp path, but good for robustness.
            if os.path.exists(meta_path):
                logger.info(f"Local metadata file {meta_path} already exists. Overwriting with fresh download.")
                # Optionally, remove it before downloading: os.remove(meta_path)

            _download_gcs_file(storage_client, bucket_name, meta_blob_name, meta_path)
            file_downloaded = True

        except ValueError as ve:  # Catch parsing errors for gcs_path
            logger.error(f"Invalid GCS path format '{gcs_meta_path_from_firestore}': {ve}")
            raise FileNotFoundError(f"Invalid GCS path format '{gcs_meta_path_from_firestore}': {str(ve)}") from ve
        except google_cloud_exceptions.NotFound as e:
            logger.warning(f"Metadata file '{gcs_meta_path_from_firestore}' not found in GCS.")
            # Propagate a clear error about GCS file not found
            raise FileNotFoundError(f"Metadata file '{gcs_meta_path_from_firestore}' not found in GCS.") from e
        except Exception as e:
            logger.error(
                f"Failed to download metadata from GCS ({gcs_meta_path_from_firestore}) for {index_name}: {e}",
                exc_info=True,
            )
            # Propagate a generic download error
            raise FileNotFoundError(
                f"Failed to download metadata from GCS ({gcs_meta_path_from_firestore}) for {index_name}: {e}"
            )

        # Load metadata from the local file
        logger.info(f"Loading metadata from: {meta_path}")
        with open(meta_path, "rb") as f:
            loaded_data = pickle.load(f)

        end_time = time.time()
        execution_time = end_time - start_time

        # Return only the metadata dictionary
        metadata = loaded_data.get("metadata", {})
        logger.info(f"Successfully loaded metadata for '{index_name}'. Execution time: {execution_time:.4f}s")
        return {
            "result": metadata,
            "meta": {"status": "success", "execution_time": execution_time, "file_downloaded": file_downloaded},
        }

    except FileNotFoundError as e:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.error(f"Error in load_metadata_from_faiss for '{index_name}': {e}")
        return {
            "error": f"Error loading metadata for '{index_name}': {str(e)}",  # Changed from "result" to "error"
            "meta": {
                "status": "error",
                "execution_time": execution_time,
                "file_downloaded": file_downloaded,
                "error_type": "FileNotFoundError",
            },
        }
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        logger.error(f"General error in load_metadata_from_faiss for '{index_name}': {e}", exc_info=True)
        return {
            "error": f"Unexpected error loading metadata for '{index_name}': {str(e)}",  # Changed from "result" to "error"
            "meta": {
                "status": "error",
                "execution_time": execution_time,
                "file_downloaded": file_downloaded,
                "error_type": "GeneralLoadError",
            },
        }
    finally:
        # Cleanup temporary metadata file
        if os.path.exists(meta_path):
            try:
                os.remove(meta_path)
                logger.info(f"Removed temporary file: {meta_path}")
            except OSError as e:
                logger.error(f"Error removing temporary file {meta_path}: {e}", exc_info=True)
        # --- REMOVED index file cleanup ---
        # if os.path.exists(index_path):
        #     try:
        #         os.remove(index_path)
        #         print(f"Removed temporary file: {index_path}")
        #     except OSError as e:
        #         print(f"Error removing temporary file {index_path}: {e}")


# Example Usage
if __name__ == "__main__":
    # Ensure FIRESTORE_PROJECT_ID is set for local testing if needed
    # os.environ["FIRESTORE_PROJECT_ID"] = "your-actual-project-id"
    logging.basicConfig(level=logging.DEBUG)
    logger.info("Running load_metadata_from_faiss example.")
    # Assume my_test_index.faiss and my_test_index.meta exist from save_metadata_to_faiss example
    test_index_name = "my_test_index"

    load_result = load_metadata_from_faiss(test_index_name)
    logger.info(f"Load Result: {load_result}")

    # Test case: File not found
    logger.info("\nTesting non-existent index:")
    non_existent_result = load_metadata_from_faiss("non_existent_index")
    logger.info(f"Non-existent index result: {non_existent_result}")
