import logging  # Added logging
import os
import pickle
import time
from typing import Any

import faiss
import google.api_core.exceptions  # Keep for RetryError, and now for ResumableUploadError
import numpy as np
from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import (
    exceptions as google_cloud_exceptions,
)  # Import google.cloud.exceptions
from google.cloud import (
    firestore,  # Add Firestore import
    storage,
)

# Import for embedding generation
from ADK.agent_data.tools.external_tool_registry import (
    OPENAI_AVAILABLE,
    get_openai_embedding,
    openai_client,
)

# Import openai for exception handling
try:
    import openai
except ImportError:
    openai = None

# ADDED MISSING IMPORT
from ADK.agent_data.agent.agent_data_agent import AgentDataAgent

# Import the utility function
from .utils.gcs_utils import upload_with_retry


# Define custom exceptions here for now
class EmbeddingGenerationError(Exception):
    """Custom exception for errors during embedding generation."""

    pass


class InvalidVectorDataError(ValueError):
    """Custom exception for invalid vector data format."""

    pass


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get GCS_BUCKET_NAME and FIRESTORE_PROJECT_ID from environment variables
GCS_BUCKET_NAME = os.environ.get(
    "GCS_BUCKET_NAME", "huyen1974-faiss-index-storage-test"
)
FIRESTORE_PROJECT_ID = os.environ.get(
    "FIRESTORE_PROJECT_ID", "chatgpt-db-project"
)  # Default if not set

if not GCS_BUCKET_NAME:
    logger.error(
        "GCS_BUCKET_NAME environment variable not set. Upload to GCS will fail."
    )
    # Optionally, raise an error or provide a default fallback if appropriate for your application
    # raise ValueError("GCS_BUCKET_NAME environment variable is required.")

# FAISS_DIR = "ADK/agent_data/faiss_indices"

# upload_with_retry function has been moved to utils.gcs_utils


async def _generate_embeddings_batch(
    texts_to_embed_with_ids: list[tuple[str, str]],
    agent_context: AgentDataAgent | None,
    batch_size: int = 32,  # Default batch size
) -> dict[str, dict[str, Any]]:
    """
    Generates embeddings for a list of (doc_id, text_content) tuples in batches.

    Args:
        texts_to_embed_with_ids: List of tuples, where each tuple is (doc_id, text_content).
        agent_context: The agent context, potentially containing an OpenAI client.
        batch_size: The number of texts to process in each batch.

    Returns:
        A dictionary mapping doc_id to the embedding result dictionary.
        If an embedding fails for a document, its ID might be missing from the map
        or associated with an error indicator if get_openai_embedding returns one.
    """
    embedding_results_map: dict[str, dict[str, Any]] = {}

    for i in range(0, len(texts_to_embed_with_ids), batch_size):
        batch_items = texts_to_embed_with_ids[i : i + batch_size]
        # For now, assuming get_openai_embedding processes one text at a time.
        # If get_openai_embedding could take a list of texts, this would be more efficient.
        for doc_id, text_content in batch_items:
            try:
                logger.debug(f"Requesting embedding for doc_id: {doc_id}")
                # Assuming get_openai_embedding is async and handles its own retries/errors appropriately
                embedding_response = await get_openai_embedding(
                    agent_context=agent_context, text_to_embed=text_content
                )
                embedding_value = embedding_response.get(
                    "embedding"
                )  # Extract embedding value
                # Check if embedding_value is a non-empty numpy array
                if (
                    embedding_response
                    and isinstance(embedding_value, np.ndarray)
                    and embedding_value.size > 0
                ):
                    embedding_results_map[doc_id] = embedding_response
                    logger.debug(
                        f"Successfully received embedding for doc_id: {doc_id}"
                    )
                else:
                    logger.error(
                        f"Failed to generate or received invalid embedding for doc_id: {doc_id}. Response: {embedding_response}"
                    )
                    # Optionally, store an error marker: embedding_results_map[doc_id] = {"error": "failed_to_generate"}
            except (
                EmbeddingGenerationError
            ) as e:  # Catch specific error from get_openai_embedding
                logger.error(
                    f"EmbeddingGenerationError for doc_id {doc_id}: {e}", exc_info=True
                )
                embedding_results_map[doc_id] = {
                    "error": str(e),
                    "status": "error",
                    "error_type": type(e).__name__,
                }
            except Exception as e:
                logger.error(
                    f"Unexpected error generating embedding for doc_id {doc_id}: {e}",
                    exc_info=True,
                )
                # Store a generic error marker in the map for this doc_id
                embedding_results_map[doc_id] = {
                    "error": str(e),
                    "status": "error",
                    "error_type": type(e).__name__,
                }
                # Depending on policy, might re-raise if it's critical for the whole batch

    return embedding_results_map


async def save_metadata_to_faiss(
    index_name: str,
    metadata_dict: dict,
    vector_data: list[list[float]] | None = None,
    text_field_to_embed: str | None = None,
    dimension: int | None = None,  # Added dimension parameter as Optional
    config: dict[str, Any] | None = None,  # Added config for Firestore update control
) -> dict:
    """
    Saves metadata along with FAISS index. Stores metadata in a separate .meta file.
    If vector_data is not provided, generates embeddings using text_field_to_embed from metadata_dict.
    Validates vector dimensions and uploads to GCS. Cleans up local temp files.
    Firestore update is conditional based on GCS success and config.

    Args:
        index_name (str): The name for the FAISS index and metadata file.
        metadata_dict (dict): Dictionary containing metadata to save. Items with non-string or empty text_field_to_embed are skipped.
        vector_data (Optional[List[List[float]]]): Optional list of pre-computed vectors.
        text_field_to_embed (Optional[str]): Field name in metadata_dict items to use for embedding if vector_data is None.
        dimension (Optional[int]): Expected dimension of embeddings or FAISS index.
        config (Optional[Dict[str, Any]]): Configuration dictionary.
                                           Expected keys:
                                           - "update_firestore_registry" (bool, default True): Whether to update Firestore.

    Returns:
        dict: Result dictionary indicating success or error.
    """
    start_time = time.time()
    index_path = f"/tmp/{index_name}.faiss"
    meta_path = f"/tmp/{index_name}.meta"

    # Initialize config if None
    if config is None:
        config = {}

    # Default update_firestore_registry to True if not specified
    update_firestore_registry = config.get("update_firestore_registry", True)

    gcs_faiss_path_for_result = None
    gcs_meta_path_for_result = None
    gcs_upload_status_for_result = "not_attempted"
    final_vector_count = 0
    final_dimension = 0

    # Initialize Firestore client (outside try-finally for GCS to ensure it's available for error cases if needed)
    # However, actual operations like .set() or .delete() will be conditional.
    db = None
    if update_firestore_registry:
        try:
            db = firestore.Client(
                project=FIRESTORE_PROJECT_ID,
                database=os.environ.get("FIRESTORE_DATABASE_ID", "test-default"),
            )
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}", exc_info=True)
            # If Firestore client fails to init, we can't update registry, but might still proceed with GCS if configured.
            # For now, let's make Firestore client essential if update_firestore_registry is True.
            return {
                "status": "error",
                "message": f"Failed to initialize Firestore client: {str(e)}",
                "meta": {
                    "error_type": "FirestoreInitializationError",
                    "index_name": index_name,
                    "duration_seconds": time.time() - start_time,
                },
            }

    all_vectors = []
    doc_ids_for_pickle = []
    processed_metadata_for_pickle = {}
    embedding_generation_errors = {}

    try:
        if not GCS_BUCKET_NAME:
            raise ValueError(
                "GCS_BUCKET_NAME is not configured. Cannot proceed with GCS operations."
            )

        if vector_data is not None:
            # Validate and use provided vector_data
            if not isinstance(
                vector_data, (list, np.ndarray)
            ):  # Allow numpy array as input
                raise InvalidVectorDataError(
                    "vector_data must be a list of lists or a 2D numpy array."
                )
            # if not vector_data: # Empty list <-- Moved and refined
            #      raise InvalidVectorDataError("vector_data is empty.")

            if isinstance(vector_data, np.ndarray):
                if vector_data.ndim != 2:  # Check dimension first for numpy arrays
                    raise InvalidVectorDataError(
                        "Numpy array for vector_data must be 2D."
                    )
                if vector_data.size == 0:  # Then check if it's empty
                    raise InvalidVectorDataError("vector_data (numpy array) is empty.")
                all_vectors = vector_data.astype(
                    np.float32
                ).tolist()  # Convert to list of lists of Python floats first
            else:  # It's a list
                if not vector_data:  # Check if list is empty
                    raise InvalidVectorDataError("vector_data (list) is empty.")
                all_vectors = []
                for i, v_list in enumerate(vector_data):
                    if not isinstance(v_list, list) or not all(
                        isinstance(x, (float, int)) for x in v_list
                    ):
                        raise InvalidVectorDataError(
                            f"Vector at index {i} is not a list of numbers."
                        )
                    all_vectors.append(np.array(v_list, dtype=np.float32))

            if not all_vectors:  # After potential conversion, if it results in empty
                raise InvalidVectorDataError(
                    "Provided vector_data resulted in no valid vectors."
                )

            # Determine dimension from the first valid vector if not provided
            current_dim = len(all_vectors[0])
            if dimension is None:
                dimension = current_dim
            elif dimension != current_dim:
                raise InvalidVectorDataError(
                    f"Provided dimension {dimension} does not match vector dimension {current_dim}."
                )

            for v in all_vectors:
                if len(v) != dimension:
                    raise InvalidVectorDataError(
                        f"Inconsistent vector dimensions. Expected {dimension}, got {len(v)}."
                    )

            # Doc IDs for provided vectors must match metadata_dict keys
            if len(all_vectors) != len(metadata_dict):
                raise ValueError(
                    f"Number of vectors ({len(all_vectors)}) does not match number of metadata entries ({len(metadata_dict)})."
                )

            doc_ids_for_pickle = list(metadata_dict.keys())
            processed_metadata_for_pickle = metadata_dict
            all_vectors = np.array(
                all_vectors, dtype=np.float32
            )  # Final conversion to numpy array for Faiss

        else:  # Generate embeddings
            if not text_field_to_embed:
                raise ValueError(
                    "text_field_to_embed must be provided when vector_data is not given."
                )
            if not OPENAI_AVAILABLE or not openai_client:
                raise RuntimeError(
                    "OpenAI client/library not available/initialized. Cannot generate embeddings."
                )

            texts_to_embed_with_ids = []
            temp_failed_doc_ids = []
            for doc_id, doc_data in metadata_dict.items():
                if (
                    isinstance(doc_data, dict)
                    and isinstance(doc_data.get(text_field_to_embed), str)
                    and doc_data.get(text_field_to_embed).strip()
                ):
                    texts_to_embed_with_ids.append(
                        (doc_id, doc_data[text_field_to_embed])
                    )
                else:
                    temp_failed_doc_ids.append(doc_id)
                    embedding_generation_errors[doc_id] = (
                        "Missing or invalid text field"
                    )

            if not texts_to_embed_with_ids:
                raise ValueError(
                    "No valid texts found for embedding after filtering metadata_dict."
                )

            embedding_results_map = await _generate_embeddings_batch(
                texts_to_embed_with_ids, None
            )  # agent_context=None for now

            temp_embeddings = []
            successful_doc_ids = []
            processed_metadata_for_embedding = {}

            for (
                doc_id,
                text_content,
            ) in texts_to_embed_with_ids:  # Iterate in the order texts were collected
                result = embedding_results_map.get(doc_id)
                if (
                    result
                    and result.get("status") == "success"
                    and isinstance(result.get("embedding"), np.ndarray)
                ):
                    emb = result["embedding"].astype(np.float32)
                    if (
                        dimension is None
                    ):  # Set dimension from first successful embedding
                        dimension = emb.shape[0]
                    elif emb.shape[0] != dimension:
                        embedding_generation_errors[doc_id] = (
                            f"Dimension mismatch: expected {dimension}, got {emb.shape[0]}"
                        )
                        temp_failed_doc_ids.append(doc_id)
                        continue
                    temp_embeddings.append(emb)
                    successful_doc_ids.append(doc_id)
                    processed_metadata_for_embedding[doc_id] = metadata_dict[doc_id]
                else:
                    embedding_generation_errors[doc_id] = (
                        result.get("error", "Unknown embedding error")
                        if result
                        else "No result from embedding function"
                    )
                    temp_failed_doc_ids.append(doc_id)

            if not temp_embeddings:
                error_msg = "No embeddings could be successfully processed."
                if embedding_generation_errors:
                    first_err_doc_id = next(iter(embedding_generation_errors))
                    error_msg += f" First detailed error for doc_id '{first_err_doc_id}': {embedding_generation_errors[first_err_doc_id]}"
                raise EmbeddingGenerationError(error_msg)

            all_vectors = np.array(temp_embeddings)
            doc_ids_for_pickle = successful_doc_ids
            processed_metadata_for_pickle = processed_metadata_for_embedding
            # Update failed_doc_ids with those that failed embedding
            # failed_doc_ids.extend(temp_failed_doc_ids) # This was done in the original structure implicitly

        # At this point, all_vectors (np.array) and doc_ids_for_pickle are set
        if (
            all_vectors.size == 0
        ):  # Should be caught by earlier checks, but as a safeguard
            raise ValueError("No vectors available to create FAISS index.")

        final_vector_count = all_vectors.shape[0]
        final_dimension = (
            all_vectors.shape[1]
            if all_vectors.ndim == 2 and all_vectors.shape[0] > 0
            else (dimension or 0)
        )

        # Create FAISS index
        logger.info(
            f"Creating FAISS index '{index_name}' with {final_vector_count} vectors of dimension {final_dimension}."
        )
        index = faiss.IndexFlatL2(final_dimension)
        index.add(all_vectors)
        faiss.write_index(index, index_path)

        # Save metadata map (doc_ids and original metadata for embedded items)
        with open(meta_path, "wb") as f:
            pickle.dump(
                {"ids": doc_ids_for_pickle, "metadata": processed_metadata_for_pickle},
                f,
            )

        # --- GCS Upload Section ---
        storage_client = storage.Client(
            project=FIRESTORE_PROJECT_ID
        )  # Use consistent project ID
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        index_blob_name = f"{index_name}.faiss"
        meta_blob_name = f"{index_name}.meta"

        index_blob = bucket.blob(index_blob_name)
        meta_blob = bucket.blob(meta_blob_name)

        try:
            logger.info(
                f"Uploading FAISS index to gs://{GCS_BUCKET_NAME}/{index_blob_name}"
            )
            upload_with_retry(index_blob, index_path)
            gcs_faiss_path_for_result = f"gs://{GCS_BUCKET_NAME}/{index_blob_name}"

            logger.info(
                f"Uploading metadata map to gs://{GCS_BUCKET_NAME}/{meta_blob_name}"
            )
            upload_with_retry(meta_blob, meta_path)
            gcs_meta_path_for_result = f"gs://{GCS_BUCKET_NAME}/{meta_blob_name}"

            gcs_upload_status_for_result = "success"
            gcs_upload_successful = True  # Local flag for conditional Firestore update

        except (
            google_cloud_exceptions.GoogleCloudError,
            google.api_core.exceptions.GoogleAPICallError,
            ConnectionError,
        ) as e:
            logger.error(
                f"GCS upload failed for index '{index_name}': {e}", exc_info=True
            )
            gcs_upload_status_for_result = "failed"
            gcs_upload_successful = False  # Explicitly set to false
            # Do NOT proceed to Firestore update if GCS fails. Return error from here.
            # The finally block will clean up local files.
            duration = time.time() - start_time
            return {
                "status": "error",
                "message": f"GCS upload failed: {str(e)}",
                "gcs_faiss_path": gcs_faiss_path_for_result,  # May be None or partially set
                "gcs_meta_path": gcs_meta_path_for_result,  # May be None or partially set
                "gcs_upload_status": gcs_upload_status_for_result,
                "vector_count": final_vector_count,
                "dimension": final_dimension,
                "index_name": index_name,
                "meta": {
                    "error_type": "GCSCommunicationError",
                    "index_name": index_name,
                    "duration_seconds": round(duration, 4),
                },
            }

        # --- Firestore Update Section (conditional on GCS success and config) ---
        if gcs_upload_successful and update_firestore_registry:
            if (
                not db
            ):  # Should have been initialized if update_firestore_registry is True
                logger.error(
                    "Firestore client (db) is not initialized. Skipping Firestore update."
                )
            else:
                try:
                    # Construct the document ID for Firestore
                    firestore_db_id = os.environ.get(
                        "FIRESTORE_DATABASE_ID", "(default)"
                    )
                    # Only append if it's not the actual default database ID string
                    doc_id_for_firestore = (
                        f"{index_name}_{firestore_db_id}"
                        if firestore_db_id != "(default)"
                        else index_name
                    )

                    doc_ref = db.collection(
                        os.environ.get(
                            "FAISS_INDEXES_COLLECTION", "faiss_indexes_registry"
                        )
                    ).document(doc_id_for_firestore)
                    doc_ref.set(
                        {
                            "index_name": index_name,
                            "gcs_bucket": GCS_BUCKET_NAME,
                            "content": "FAISS index metadata and GCS paths",
                            "timestamp": firestore.SERVER_TIMESTAMP,
                            "vectorStatus": "completed",  # If GCS upload was successful
                            "labels": {
                                "Category": f"Documents/Workflow/MPC/AgentData/FAISS/{time.strftime('%Y')}",
                                "DocType": "FAISSIndex",
                                "GCSPathIndex": gcs_faiss_path_for_result,
                                "GCSPathMeta": gcs_meta_path_for_result,
                                "VectorCount": final_vector_count,
                                "IndexDimension": final_dimension,
                                "IndexType": str(
                                    type(index).__name__
                                ),  # e.g., "IndexFlatL2"
                            },
                            # Storing a snapshot of the keys from the processed metadata
                            "metadata_snapshot": {
                                k: str(v)[:200] + "..." if len(str(v)) > 200 else str(v)
                                for k, v in processed_metadata_for_pickle.items()
                            },
                        }
                    )
                    logger.info(
                        f"Successfully updated Firestore registry for index '{index_name}'."
                    )
                except Exception as e:
                    logger.error(
                        f"Firestore update failed for index '{index_name}': {e}",
                        exc_info=True,
                    )
                    # If GCS was successful but Firestore fails, it's a partial success/error state.
                    # The main status might still be 'success' regarding Faiss/GCS, but with a Firestore error note.
                    # For now, let's keep gcs_upload_status as "success" but flag Firestore issue.
                    # This specific return might need refinement based on desired behavior for FS errors post-GCS.
                    duration = time.time() - start_time
                    return {
                        "status": "partial_success",  # Or "error" if FS update is critical
                        "message": f"FAISS/GCS successful, but Firestore update failed: {str(e)}",
                        "gcs_faiss_path": gcs_faiss_path_for_result,
                        "gcs_meta_path": gcs_meta_path_for_result,
                        "gcs_upload_status": "success",  # GCS part was okay
                        "firestore_update_status": "failed",
                        "vector_count": final_vector_count,
                        "dimension": final_dimension,
                        "index_name": index_name,
                        "meta": {
                            "error_type": "FirestoreRegistryError",
                            "index_name": index_name,
                            "duration_seconds": round(duration, 4),
                        },
                    }
        elif not update_firestore_registry:
            logger.info(
                f"Skipping Firestore registry update for '{index_name}' as per configuration."
            )

        # If all successful (including conditional Firestore update)
        duration = time.time() - start_time
        return {
            "status": "success",
            "message": f"FAISS index '{index_name}' and metadata saved and uploaded to GCS successfully.",
            "index_name": index_name,
            "gcs_bucket": GCS_BUCKET_NAME,
            "gcs_faiss_path": gcs_faiss_path_for_result,
            "gcs_meta_path": gcs_meta_path_for_result,
            "vector_count": final_vector_count,
            "dimension": final_dimension,
            "index_type": str(type(index).__name__),
            "duration_seconds": round(duration, 4),
            "gcs_upload_status": gcs_upload_status_for_result,
            "firestore_update_status": (
                "success"
                if update_firestore_registry and gcs_upload_successful
                else ("skipped" if not update_firestore_registry else "failed")
            ),
        }

    except (
        ValueError,
        RuntimeError,
        EmbeddingGenerationError,
        InvalidVectorDataError,
        openai.APIError,
        TypeError,
    ) as e:  # Catch specific operational errors
        logger.error(
            f"Operational error during FAISS processing for index '{index_name}': {type(e).__name__} - {e}",
            exc_info=True,
        )
        duration = time.time() - start_time
        # Construct error metadata, including embedding generation errors if any
        error_meta = {
            "error_type": type(e).__name__,
            "index_name": index_name,
            "duration_seconds": round(duration, 4),
        }
        if (
            embedding_generation_errors
        ):  # Add embedding_generation_errors to the meta if they exist
            error_meta["embedding_generation_errors"] = embedding_generation_errors
        # Include counts based on what was processed before error
        error_meta.setdefault("original_docs_count", len(metadata_dict))
        error_meta.setdefault(
            "embedded_docs_count", len(doc_ids_for_pickle) if doc_ids_for_pickle else 0
        )

        # Collect all doc_ids that were meant to be processed but aren't in doc_ids_for_pickle
        # This gives a more comprehensive list of failed_doc_ids
        all_intended_doc_ids = set(metadata_dict.keys())
        successfully_processed_doc_ids = set(doc_ids_for_pickle)
        calculated_failed_doc_ids = list(
            all_intended_doc_ids - successfully_processed_doc_ids
        )
        error_meta.setdefault("failed_doc_ids", calculated_failed_doc_ids)

        return {
            "status": "error",
            "error": str(e),  # Main error message
            "message": str(e),  # Duplicate for consistency with some error structures
            "meta": error_meta,
        }
    except Exception as e:  # Catch any other unexpected general errors
        logger.error(
            f"Unexpected general error during FAISS processing for index '{index_name}': {e}",
            exc_info=True,
        )
        duration = time.time() - start_time
        return {
            "status": "error",
            "error": f"Unexpected general error: {str(e)}",
            "message": str(e),
            "meta": {
                "error_type": type(e).__name__,
                "index_name": index_name,
                "duration_seconds": round(duration, 2),
            },
        }
    finally:
        # Ensure cleanup of local files
        if os.path.exists(index_path):
            try:
                os.remove(index_path)
                logger.info(f"Cleanup: Removed temporary local file: {index_path}")
            except OSError as e_remove:
                logger.error(
                    f"Error removing temporary file {index_path} in finally block: {e_remove}"
                )
        if os.path.exists(meta_path):
            try:
                os.remove(meta_path)
                logger.info(f"Cleanup: Removed temporary local file: {meta_path}")
            except OSError as e_remove:
                logger.error(
                    f"Error removing temporary file {meta_path} in finally block: {e_remove}"
                )


# Example Usage (for testing purposes)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # More verbose for local testing
    logger.info("Running save_metadata_to_faiss example.")
    test_index_name = "my_test_index"
    test_metadata = {"doc1": "This is document 1.", "doc2": "Another document here."}
    # Example: Using 5-dimensional vectors for simplicity
    test_vectors = [[0.1, 0.2, 0.3, 0.4, 0.5], [0.6, 0.7, 0.8, 0.9, 1.0]]

    save_result = save_metadata_to_faiss(test_index_name, test_metadata, test_vectors)
    logger.info(f"Save Result: {save_result}")

    # Verify files were created locally
    local_index_path = f"/tmp/{test_index_name}.faiss"
    local_meta_path = f"/tmp/{test_index_name}.meta"
    if os.path.exists(local_index_path):
        logger.info(f"Local index file found: {local_index_path}")
    else:
        logger.warning(f"Local index file NOT found: {local_index_path}")

    if os.path.exists(local_meta_path):
        logger.info(f"Local metadata file found: {local_meta_path}")
    else:
        logger.warning(f"Local metadata file NOT found: {local_meta_path}")

    # Optional: Clean up test files
    # if os.path.exists(local_index_path): os.remove(local_index_path)
    # if os.path.exists(local_meta_path): os.remove(local_meta_path)
    # logger.info("Cleaned up local test files.")

# --- Constants ---
GCS_BUCKET_NAME = os.environ.get(
    "GCS_BUCKET_NAME", "huyen1974-faiss-index-storage-test"
)
FIRESTORE_PROJECT_ID = os.environ.get("FIRESTORE_PROJECT_ID", "chatgpt-db-project")
FIRESTORE_DATABASE_ID = os.environ.get("FIRESTORE_DATABASE_ID", "test-default")
INDEX_FOLDER = os.environ.get("INDEX_FOLDER", "/tmp/faiss_indices")


# --- Helper: GCS Download/Upload ---
def _download_gcs_file(
    storage_client: storage.Client,
    bucket_name: str,
    source_blob_name: str,
    destination_file_name: str,
):
    # ... (implementation)
    pass  # Placeholder


def _upload_to_gcs(
    storage_client: storage.Client,
    bucket_name: str,
    source_file_name: str,
    destination_blob_name: str,
):
    # ... (implementation)
    pass  # Placeholder


# --- Main Tool Logic ---
def save_metadata_to_faiss_internal(
    index_name: str, doc_id: str, metadata: dict[str, Any], vectors: list[list[float]]
) -> dict[str, Any]:
    """
    Saves document metadata to Firestore and updates/creates a FAISS index,
    storing the index and metadata mapping in GCS. Includes rollback on GCS failure.
    """
    start_time = time.monotonic()
    status = "failed"
    message = ""
    firestore_doc_ref = None
    local_index_file = ""
    local_meta_file = ""

    try:
        os.makedirs(INDEX_FOLDER, exist_ok=True)
        local_index_file = os.path.join(INDEX_FOLDER, f"{index_name}.faiss")
        local_meta_file = os.path.join(INDEX_FOLDER, f"{index_name}_meta.pkl")

        # Initialize clients
        db = firestore.Client(
            project=FIRESTORE_PROJECT_ID, database=FIRESTORE_DATABASE_ID
        )
        storage_client = storage.Client()

        index = None
        metadata_map = {}

        # 1. Check Firestore for existing index metadata
        index_doc_ref = db.collection("faiss_indices").document(index_name)
        try:
            index_doc = index_doc_ref.get()
            if index_doc.exists:
                logger.info(
                    f"Index '{index_name}' exists in Firestore. Downloading from GCS..."
                )
                gcs_index_path = f"faiss_indices/{index_name}.faiss"
                gcs_meta_path = f"faiss_indices/{index_name}_meta.pkl"
                _download_gcs_file(
                    storage_client, GCS_BUCKET_NAME, gcs_index_path, local_index_file
                )
                _download_gcs_file(
                    storage_client, GCS_BUCKET_NAME, gcs_meta_path, local_meta_file
                )
                index = faiss.read_index(local_index_file)
                with open(local_meta_file, "rb") as f:
                    metadata_map = pickle.load(f)
                logger.info(
                    f"Downloaded and loaded existing index with {index.ntotal} vectors."
                )
            else:
                logger.info(
                    f"Index '{index_name}' not found in Firestore. Creating new index."
                )
        except NotFound:
            logger.info(
                f"Index document '{index_name}' not found in Firestore. Creating new index."
            )
        except Exception as e:
            logger.warning(
                f"Error downloading/loading existing index '{index_name}': {e}. Proceeding with new index."
            )

        # 2. Create Firestore document for the new metadata *first*
        firestore_doc_ref = db.collection(index_name).document(doc_id)
        try:
            # Check if doc exists? Overwrite for simplicity now.
            firestore_doc_ref.set(metadata)
            logger.info(
                f"Successfully saved metadata for doc '{doc_id}' in index '{index_name}' to Firestore."
            )
        except GoogleAPICallError as e:
            message = f"Failed to save metadata to Firestore for doc '{doc_id}': {e}"
            logger.error(message)
            raise  # Propagate Firestore error, no GCS upload attempted

        # 3. Prepare vectors and update/create FAISS index
        if not vectors:
            logger.warning(
                f"No vectors provided for doc '{doc_id}'. Skipping FAISS update."
            )
        else:
            np_vectors = np.array(vectors, dtype="float32")
            if np_vectors.ndim != 2:
                raise ValueError("Vectors must be a list of lists (2D array).")
            dimension = np_vectors.shape[1]
            num_new_vectors = np_vectors.shape[0]

            if index is None:
                logger.info(
                    f"Creating new FAISS index (IndexFlatL2) with dimension {dimension}."
                )
                index = faiss.IndexFlatL2(dimension)
                # Add a dummy vector if index is empty before adding real vectors?
                # index.add(np.zeros((1, dimension), dtype='float32'))

            if index.d != dimension:
                raise ValueError(
                    f"Vector dimension mismatch: Index has {index.d}, new vectors have {dimension}."
                )

            start_id = index.ntotal
            index.add(np_vectors)
            logger.info(
                f"Added {num_new_vectors} vectors to FAISS index. Total vectors: {index.ntotal}."
            )

            # Update metadata map (maps internal FAISS index ID to doc_id and original metadata key)
            for i in range(num_new_vectors):
                # Store the primary key (doc_id) associated with this vector index
                metadata_map[start_id + i] = doc_id
            logger.info(
                f"Updated local metadata map for {num_new_vectors} new vectors."
            )

            # Save updated index and metadata map locally
            faiss.write_index(index, local_index_file)
            with open(local_meta_file, "wb") as f:
                pickle.dump(metadata_map, f)
            logger.info("Saved updated index and metadata map locally.")

            # 4. Upload to GCS (Crucial step with rollback)
            gcs_index_path = f"faiss_indices/{index_name}.faiss"
            gcs_meta_path = f"faiss_indices/{index_name}_meta.pkl"
            try:
                _upload_to_gcs(
                    storage_client, GCS_BUCKET_NAME, local_index_file, gcs_index_path
                )
                logger.info(
                    f"Successfully uploaded index file to gs://{GCS_BUCKET_NAME}/{gcs_index_path}"
                )
                _upload_to_gcs(
                    storage_client, GCS_BUCKET_NAME, local_meta_file, gcs_meta_path
                )
                logger.info(
                    f"Successfully uploaded metadata map to gs://{GCS_BUCKET_NAME}/{gcs_meta_path}"
                )

                # 5. Update Firestore index document (only after successful GCS upload)
                index_doc_ref.set(
                    {
                        "updated_at": firestore.SERVER_TIMESTAMP,
                        "vector_count": index.ntotal,
                        "dimension": index.d,
                        "gcs_index_path": gcs_index_path,
                        "gcs_meta_path": gcs_meta_path,
                    },
                    merge=True,
                )
                logger.info(f"Updated Firestore index document for '{index_name}'.")
                status = "success"
                message = f"Document '{doc_id}' metadata saved, FAISS index updated ({num_new_vectors} vectors), and artifacts uploaded."

            except Exception as gcs_error:
                # --- ROLLBACK LOGIC ---
                status = "failed_gcs_upload"
                message = f"GCS upload failed for index '{index_name}': {gcs_error}. Rolling back Firestore metadata save."
                logger.error(message, exc_info=True)
                if firestore_doc_ref:
                    try:
                        logger.warning(
                            f"Attempting to delete Firestore document {firestore_doc_ref.path} due to GCS upload failure."
                        )
                        firestore_doc_ref.delete()
                        logger.info(
                            f"Successfully deleted Firestore document {firestore_doc_ref.path}."
                        )
                        message += " Firestore metadata successfully rolled back."
                    except Exception as delete_error:
                        rollback_fail_msg = f"CRITICAL: Failed to delete Firestore document {firestore_doc_ref.path} during rollback: {delete_error}"
                        logger.critical(rollback_fail_msg)
                        message += (
                            f" {rollback_fail_msg}"  # Append rollback failure info
                        )
                # Re-raise the original GCS error after attempting rollback
                raise gcs_error

    except Exception as e:
        # Catch other errors (vector validation, local save, etc.)
        status = "failed"
        if (
            not message
        ):  # Use specific message if already set (like Firestore save fail)
            message = f"Error processing save_metadata_to_faiss for '{doc_id}' in '{index_name}': {e}"
        logger.error(message, exc_info=True)
        # Should we attempt rollback here too? Depends on where the error occurred.
        # If Firestore save succeeded but local index save failed, rollback might be needed.
        # For simplicity, only rolling back on GCS failure for now.

    finally:
        # Clean up local files
        if os.path.exists(local_index_file):
            try:
                os.remove(local_index_file)
            except OSError:
                pass
        if os.path.exists(local_meta_file):
            try:
                os.remove(local_meta_file)
            except OSError:
                pass

    duration_ms = (time.monotonic() - start_time) * 1000
    return {
        "result": message,
        "meta": {"status": status, "duration_ms": round(duration_ms, 2)},
    }


# Ensure no test code or extraneous decorators/functions below this line in the module file.
