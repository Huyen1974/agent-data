import os
import logging
from typing import Dict, Any, Union, List

# Attempt to import AsyncClient, fall back for environments where it might not be immediately available
# or to allow type hinting without a hard dependency for non-Firestore use cases.
try:
    from google.cloud import firestore

    # Explicitly use AsyncClient for async operations
    if hasattr(firestore, "AsyncClient"):
        FirestoreAsyncClient = firestore.AsyncClient
    else:
        # Fallback or define a placeholder if direct async client isn't found
        # This path might indicate an older library version or an issue.
        # For type hinting or conditional logic, this might be okay.
        # For actual async operations, firestore.AsyncClient is needed.
        logging.warning("firestore.AsyncClient not found, Firestore async operations might be affected.")
        FirestoreAsyncClient = None
except ImportError:
    logging.warning("google-cloud-firestore library not found. FirestoreMetadataManager will not function.")
    firestore = None
    FirestoreAsyncClient = None

logger = logging.getLogger(__name__)


class FirestoreMetadataManager:
    def __init__(self, project_id: str = None, collection_name: str = None):
        if not FirestoreAsyncClient:
            raise ImportError("Firestore AsyncClient is not available. Cannot initialize FirestoreMetadataManager.")

        self.project_id = project_id or os.getenv("FIRESTORE_PROJECT_ID")
        if not self.project_id:
            # Fallback to a default project ID if you have one, or raise an error.
            # For this example, let's assume it might be implicitly handled by gcloud environment.
            logger.info("FIRESTORE_PROJECT_ID not explicitly set, relying on gcloud environment.")

        # Default collection name if not provided or found in env
        self.collection_name = collection_name or os.getenv("QDRANT_METADATA_COLLECTION", "qdrant_vector_metadata")

        try:
            self.db = FirestoreAsyncClient(project=self.project_id)
            logger.info(
                f"FirestoreMetadataManager initialized for project '{self.project_id}' and collection '{self.collection_name}'."
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize Firestore AsyncClient for project '{self.project_id}': {e}", exc_info=True
            )
            # Depending on the application's needs, you might re-raise or handle this.
            # For now, if the client fails to initialize, subsequent operations will fail.
            self.db = None  # Ensure db is None if initialization fails
            raise ConnectionError(f"Could not connect to Firestore: {e}")

    async def save_metadata(self, point_id: Union[str, int], metadata: Dict[str, Any]) -> None:
        """
        Saves or updates metadata for a given point_id in Firestore.
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot save metadata.")
            return

        doc_id = str(point_id)  # Firestore document IDs must be strings
        doc_ref = self.db.collection(self.collection_name).document(doc_id)
        try:
            # Firestore's set operation with merge=True can be used for upsert-like behavior,
            # but if you want to completely overwrite, use set without merge.
            # For typical metadata updates, a full set is often desired.
            await doc_ref.set(metadata)
            logger.debug(
                f"Successfully saved metadata for point_id '{doc_id}' in Firestore collection '{self.collection_name}'."
            )
        except Exception as e:
            logger.error(f"Failed to save metadata for point_id '{doc_id}' to Firestore: {e}", exc_info=True)
            # Optionally re-raise or handle as per application error strategy
            raise

    async def delete_metadata(self, point_id: Union[str, int]) -> None:
        """
        Deletes metadata for a given point_id from Firestore.
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot delete metadata.")
            return

        doc_id = str(point_id)  # Firestore document IDs must be strings
        doc_ref = self.db.collection(self.collection_name).document(doc_id)
        try:
            await doc_ref.delete()
            logger.debug(
                f"Successfully deleted metadata for point_id '{doc_id}' from Firestore collection '{self.collection_name}'."
            )
        except Exception as e:
            # Firestore's delete is generally idempotent; if doc doesn't exist, it won't error.
            # However, other errors (permissions, network) can occur.
            logger.error(f"Failed to delete metadata for point_id '{doc_id}' from Firestore: {e}", exc_info=True)
            # Optionally re-raise or handle
            raise

    async def batch_save_metadata(self, metadata_batch: Dict[Union[str, int], Dict[str, Any]]) -> None:
        """
        Saves or updates a batch of metadata in Firestore using a batch writer.
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot batch save metadata.")
            return
        if not metadata_batch:
            logger.info("No metadata provided for batch save.")
            return

        batch = self.db.batch()
        for point_id, metadata in metadata_batch.items():
            doc_id = str(point_id)
            doc_ref = self.db.collection(self.collection_name).document(doc_id)
            batch.set(doc_ref, metadata)

        try:
            await batch.commit()
            logger.debug(
                f"Successfully batch saved metadata for {len(metadata_batch)} items in Firestore collection '{self.collection_name}'."
            )
        except Exception as e:
            logger.error(f"Failed to batch save metadata to Firestore: {e}", exc_info=True)
            raise

    async def batch_delete_metadata(self, point_ids: List[Union[str, int]]) -> None:
        """
        Deletes a batch of metadata from Firestore using a batch writer.
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot batch delete metadata.")
            return
        if not point_ids:
            logger.info("No point_ids provided for batch delete.")
            return

        batch = self.db.batch()
        for point_id in point_ids:
            doc_id = str(point_id)
            doc_ref = self.db.collection(self.collection_name).document(doc_id)
            batch.delete(doc_ref)

        try:
            await batch.commit()
            logger.debug(
                f"Successfully batch deleted metadata for {len(point_ids)} items from Firestore collection '{self.collection_name}'."
            )
        except Exception as e:
            logger.error(f"Failed to batch delete metadata from Firestore: {e}", exc_info=True)
            raise
