import os
import logging
from typing import Dict, Any, Union, List, Optional
from datetime import datetime

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

    async def _check_document_exists(self, doc_ref) -> bool:
        """
        Optimized check for document existence using minimal RU consumption.
        CLI 140e.2 RU optimization: Uses select() with limit(1) to minimize read units.

        Args:
            doc_ref: Firestore document reference

        Returns:
            True if document exists, False otherwise
        """
        try:
            # Use select() with a minimal field and limit(1) to reduce RU consumption
            # This reads only the document ID field instead of the entire document
            query = (
                self.db.collection(self.collection_name)
                .select(["__name__"])
                .limit(1)
                .where("__name__", "==", doc_ref.path)
            )
            docs = [doc async for doc in query.stream()]
            return len(docs) > 0
        except Exception as e:
            # Fallback to standard exists check if optimized query fails
            logger.warning(f"Optimized existence check failed, falling back to standard method: {e}")
            doc = await doc_ref.get()
            return doc.exists

    async def _get_document_for_versioning(self, doc_ref):
        """
        Get document with optimized RU usage for versioning.
        CLI 140e.2 RU optimization: Only fetches full document if it exists.

        Args:
            doc_ref: Firestore document reference

        Returns:
            Document snapshot or None
        """
        try:
            # First check if document exists with minimal RU
            exists = await self._check_document_exists(doc_ref)
            if not exists:
                # Return a mock document snapshot for non-existent documents
                class MockDocSnapshot:
                    exists = False

                    def to_dict(self):
                        return {}

                return MockDocSnapshot()

            # Only fetch full document if it exists
            return await doc_ref.get()
        except Exception as e:
            logger.warning(f"Optimized document fetch failed, falling back to standard method: {e}")
            return await doc_ref.get()

    async def save_metadata(self, point_id: Union[str, int], metadata: Dict[str, Any]) -> None:
        """
        Saves or updates metadata for a given point_id in Firestore with versioning support.
        CLI 140e.2 RU optimization: Uses optimized existence checks to reduce read units.

        Args:
            point_id: Unique identifier for the document
            metadata: Metadata dictionary to save
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot save metadata.")
            return

        # Validate metadata before saving
        validation_result = self._validate_metadata(metadata)
        if not validation_result["valid"]:
            logger.error(f"Metadata validation failed: {validation_result['errors']}")
            raise ValueError(f"Invalid metadata: {validation_result['errors']}")

        doc_id = str(point_id)  # Firestore document IDs must be strings
        doc_ref = self.db.collection(self.collection_name).document(doc_id)

        try:
            # Get existing document to handle versioning (RU optimized)
            existing_doc = await self._get_document_for_versioning(doc_ref)

            # Validate version increment if document exists
            if existing_doc.exists:
                existing_data = existing_doc.to_dict()
                if not self._validate_version_increment(existing_data, metadata):
                    logger.warning(f"Version increment validation failed for {doc_id}")

            # Prepare versioned metadata
            versioned_metadata = await self._prepare_versioned_metadata(metadata, existing_doc)

            # Save with versioning and hierarchy support
            await doc_ref.set(versioned_metadata)
            logger.debug(
                f"Successfully saved metadata for point_id '{doc_id}' in Firestore collection '{self.collection_name}' with version {versioned_metadata.get('version', 1)}. RU optimized."
            )
        except Exception as e:
            logger.error(f"Failed to save metadata for point_id '{doc_id}' to Firestore: {e}", exc_info=True)
            # Optionally re-raise or handle as per application error strategy
            raise

    async def _prepare_versioned_metadata(self, metadata: Dict[str, Any], existing_doc) -> Dict[str, Any]:
        """
        Prepare metadata with versioning and hierarchical structure.

        Args:
            metadata: New metadata to save
            existing_doc: Existing Firestore document snapshot

        Returns:
            Enhanced metadata with versioning and hierarchy
        """
        # Start with the provided metadata
        versioned_metadata = metadata.copy()

        # Handle versioning
        current_version = 1
        if existing_doc.exists:
            existing_data = existing_doc.to_dict()
            current_version = existing_data.get("version", 0) + 1

            # Store previous version in history
            if "version_history" not in versioned_metadata:
                versioned_metadata["version_history"] = existing_data.get("version_history", [])

            # Add current version to history (keep last 10 versions)
            version_entry = {
                "version": existing_data.get("version", 0),
                "timestamp": existing_data.get("lastUpdated", datetime.utcnow().isoformat()),
                "changes": self._detect_changes(existing_data, metadata),
            }
            versioned_metadata["version_history"].append(version_entry)

            # Keep only last 10 versions
            if len(versioned_metadata["version_history"]) > 10:
                versioned_metadata["version_history"] = versioned_metadata["version_history"][-10:]

        # Set current version and timestamp
        versioned_metadata["version"] = current_version
        versioned_metadata["lastUpdated"] = datetime.utcnow().isoformat()
        versioned_metadata["createdAt"] = versioned_metadata.get("createdAt", datetime.utcnow().isoformat())

        # Ensure hierarchical structure (level_1 through level_6)
        versioned_metadata = self._ensure_hierarchical_structure(versioned_metadata)

        return versioned_metadata

    def _detect_changes(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> List[str]:
        """
        Detect changes between old and new metadata.

        Args:
            old_data: Previous metadata
            new_data: New metadata

        Returns:
            List of changed field names
        """
        changes = []

        # Check for modified fields
        for key, new_value in new_data.items():
            if key in ["version", "lastUpdated", "version_history"]:
                continue  # Skip versioning fields

            old_value = old_data.get(key)
            if old_value != new_value:
                changes.append(f"modified:{key}")

        # Check for removed fields
        for key in old_data.keys():
            if key not in new_data and key not in ["version", "lastUpdated", "version_history"]:
                changes.append(f"removed:{key}")

        # Check for added fields
        for key in new_data.keys():
            if key not in old_data:
                changes.append(f"added:{key}")

        return changes

    def _ensure_hierarchical_structure(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure metadata has hierarchical structure with level_1 through level_6.

        Args:
            metadata: Metadata dictionary

        Returns:
            Metadata with hierarchical structure
        """
        # Initialize hierarchy levels if not present
        hierarchy_levels = ["level_1", "level_2", "level_3", "level_4", "level_5", "level_6"]

        for level in hierarchy_levels:
            if level not in metadata:
                metadata[level] = None

        # Auto-populate hierarchy based on existing metadata
        if metadata.get("level_1") is None:
            # Try to infer level_1 from document type or category
            if "doc_type" in metadata:
                metadata["level_1"] = metadata["doc_type"]
            elif "category" in metadata:
                metadata["level_1"] = metadata["category"]
            elif "source" in metadata:
                metadata["level_1"] = metadata["source"]
            else:
                metadata["level_1"] = "document"

        if metadata.get("level_2") is None and "tag" in metadata:
            metadata["level_2"] = metadata["tag"]

        if metadata.get("level_3") is None and "author" in metadata:
            metadata["level_3"] = metadata["author"]

        if metadata.get("level_4") is None and "year" in metadata:
            metadata["level_4"] = str(metadata["year"])

        if metadata.get("level_5") is None and "language" in metadata:
            metadata["level_5"] = metadata["language"]

        if metadata.get("level_6") is None and "format" in metadata:
            metadata["level_6"] = metadata["format"]

        return metadata

    async def get_metadata_with_version(
        self, point_id: Union[str, int], version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve metadata for a specific version.

        Args:
            point_id: Document identifier
            version: Specific version to retrieve (None for latest)

        Returns:
            Metadata dictionary or None if not found
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot get metadata.")
            return None

        doc_id = str(point_id)
        doc_ref = self.db.collection(self.collection_name).document(doc_id)

        try:
            doc = await doc_ref.get()
            if not doc.exists:
                return None

            data = doc.to_dict()

            # Return latest version if no specific version requested
            if version is None:
                return data

            # Return specific version from history
            if version == data.get("version"):
                return data

            # Search in version history
            version_history = data.get("version_history", [])
            for version_entry in version_history:
                if version_entry.get("version") == version:
                    # Reconstruct metadata for this version (simplified approach)
                    return {
                        "version": version,
                        "timestamp": version_entry.get("timestamp"),
                        "changes": version_entry.get("changes"),
                        "note": "Historical version - partial data",
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to get metadata for point_id '{doc_id}' from Firestore: {e}", exc_info=True)
            return None

    async def get_hierarchy_tree(self, level_filter: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get hierarchical tree structure of all documents.

        Args:
            level_filter: Optional filter for specific hierarchy levels

        Returns:
            Hierarchical tree structure
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot get hierarchy tree.")
            return {}

        try:
            collection_ref = self.db.collection(self.collection_name)

            # Apply filters if provided
            query = collection_ref
            if level_filter:
                for level, value in level_filter.items():
                    if level in ["level_1", "level_2", "level_3", "level_4", "level_5", "level_6"]:
                        query = query.where(level, "==", value)

            docs = query.stream()

            # Build hierarchy tree
            tree = {}
            async for doc in docs:
                data = doc.to_dict()
                self._add_to_tree(tree, data, doc.id)

            return tree

        except Exception as e:
            logger.error(f"Failed to get hierarchy tree from Firestore: {e}", exc_info=True)
            return {}

    def _add_to_tree(self, tree: Dict[str, Any], data: Dict[str, Any], doc_id: str):
        """
        Add document to hierarchy tree structure.

        Args:
            tree: Tree structure to add to
            data: Document data
            doc_id: Document ID
        """
        current_level = tree

        # Navigate through hierarchy levels
        for level in ["level_1", "level_2", "level_3", "level_4", "level_5", "level_6"]:
            level_value = data.get(level)
            if level_value is None:
                break

            if level_value not in current_level:
                current_level[level_value] = {"_documents": [], "_children": {}}

            current_level = current_level[level_value]["_children"]

        # Add document to the appropriate level
        if "_documents" not in current_level:
            current_level["_documents"] = []

        current_level["_documents"].append(
            {
                "doc_id": doc_id,
                "version": data.get("version", 1),
                "lastUpdated": data.get("lastUpdated"),
                "summary": data.get("content_preview", "")[:100],
            }
        )

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

    async def _batch_check_documents_exist(self, doc_ids: List[str]) -> Dict[str, bool]:
        """
        Batch check for document existence using optimized RU consumption.
        CLI 140e.2 RU optimization: Uses select() queries to minimize read units.

        Args:
            doc_ids: List of document IDs to check

        Returns:
            Dictionary mapping doc_id to existence boolean
        """
        existence_map = {}

        try:
            # Use select() query to check existence with minimal RU
            # Query for documents that exist in the batch
            doc_refs = [self.db.collection(self.collection_name).document(doc_id) for doc_id in doc_ids]
            doc_paths = [doc_ref.path for doc_ref in doc_refs]

            # Query existing documents with minimal field selection
            query = self.db.collection(self.collection_name).select(["__name__"]).where("__name__", "in", doc_paths)
            existing_docs = [doc async for doc in query.stream()]
            existing_paths = {doc.reference.path for doc in existing_docs}

            # Map existence for all requested documents
            for doc_id, doc_path in zip(doc_ids, doc_paths):
                existence_map[doc_id] = doc_path in existing_paths

        except Exception as e:
            logger.warning(f"Batch existence check failed, falling back to individual checks: {e}")
            # Fallback to individual existence checks
            for doc_id in doc_ids:
                doc_ref = self.db.collection(self.collection_name).document(doc_id)
                try:
                    doc = await doc_ref.get()
                    existence_map[doc_id] = doc.exists
                except Exception as individual_error:
                    logger.warning(f"Individual existence check failed for {doc_id}: {individual_error}")
                    existence_map[doc_id] = False

        return existence_map

    async def batch_save_metadata(self, metadata_batch: Dict[Union[str, int], Dict[str, Any]]) -> None:
        """
        Saves or updates a batch of metadata in Firestore using a batch writer with versioning support.
        CLI 140e.2 RU optimization: Uses batch existence checks to reduce read units.
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot batch save metadata.")
            return
        if not metadata_batch:
            logger.info("No metadata provided for batch save.")
            return

        batch = self.db.batch()
        doc_ids = [str(point_id) for point_id in metadata_batch.keys()]

        # Batch check for document existence (RU optimized)
        existence_map = await self._batch_check_documents_exist(doc_ids)

        # Process each document for versioning
        for point_id, metadata in metadata_batch.items():
            doc_id = str(point_id)
            doc_ref = self.db.collection(self.collection_name).document(doc_id)

            try:
                # Use optimized existence check result
                if existence_map.get(doc_id, False):
                    # Document exists, fetch full document for versioning
                    existing_doc = await doc_ref.get()
                else:
                    # Document doesn't exist, create mock snapshot
                    class MockDocSnapshot:
                        exists = False

                        def to_dict(self):
                            return {}

                    existing_doc = MockDocSnapshot()

                versioned_metadata = await self._prepare_versioned_metadata(metadata, existing_doc)
                batch.set(doc_ref, versioned_metadata)
            except Exception as e:
                logger.error(f"Failed to prepare versioned metadata for {doc_id}: {e}")
                # Continue with other documents
                continue

        try:
            await batch.commit()
            logger.debug(
                f"Successfully batch saved metadata for {len(metadata_batch)} items in Firestore collection '{self.collection_name}'. RU optimized."
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

    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate metadata structure and content.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Validation result with 'valid' boolean and 'errors' list
        """
        errors = []

        # Check required fields
        required_fields = ["doc_id"]
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")

        # Validate data types
        if "doc_id" in metadata and not isinstance(metadata["doc_id"], str):
            errors.append("doc_id must be a string")

        if "version" in metadata and not isinstance(metadata["version"], int):
            errors.append("version must be an integer")

        # Validate hierarchy levels
        hierarchy_levels = ["level_1", "level_2", "level_3", "level_4", "level_5", "level_6"]
        for level in hierarchy_levels:
            if level in metadata and metadata[level] is not None:
                if not isinstance(metadata[level], str):
                    errors.append(f"{level} must be a string or None")
                elif len(metadata[level]) > 100:
                    errors.append(f"{level} must be 100 characters or less")

        # Validate content size limits
        if "original_text" in metadata and len(str(metadata["original_text"])) > 50000:
            errors.append("original_text exceeds 50KB limit")

        # Validate timestamp formats
        timestamp_fields = ["lastUpdated", "createdAt"]
        for field in timestamp_fields:
            if field in metadata and metadata[field]:
                try:
                    datetime.fromisoformat(metadata[field].replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"{field} must be a valid ISO format timestamp")

        return {"valid": len(errors) == 0, "errors": errors}

    def _validate_version_increment(self, existing_data: Dict[str, Any], new_metadata: Dict[str, Any]) -> bool:
        """
        Validate that version increments are logical.

        Args:
            existing_data: Current document data
            new_metadata: New metadata being saved

        Returns:
            True if version increment is valid
        """
        existing_version = existing_data.get("version", 0)

        # If new metadata doesn't specify version, it's valid (will be auto-incremented)
        if "version" not in new_metadata:
            return True

        new_version = new_metadata.get("version", 0)

        # Version should not decrease
        if new_version < existing_version:
            logger.warning(f"Version decrease detected: {existing_version} -> {new_version}")
            return False

        # Version should not skip numbers (increment by 1)
        if new_version > existing_version + 1:
            logger.warning(f"Version skip detected: {existing_version} -> {new_version}")
            return False

        return True

    async def get_metadata_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the metadata collection.

        Returns:
            Dictionary with collection statistics
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot get statistics.")
            return {}

        try:
            collection_ref = self.db.collection(self.collection_name)
            docs = collection_ref.stream()

            stats = {
                "total_documents": 0,
                "hierarchy_distribution": {},
                "version_distribution": {},
                "latest_update": None,
                "oldest_document": None,
            }

            async for doc in docs:
                data = doc.to_dict()
                stats["total_documents"] += 1

                # Track hierarchy distribution
                level_1 = data.get("level_1", "unknown")
                if level_1 not in stats["hierarchy_distribution"]:
                    stats["hierarchy_distribution"][level_1] = 0
                stats["hierarchy_distribution"][level_1] += 1

                # Track version distribution
                version = data.get("version", 1)
                if version not in stats["version_distribution"]:
                    stats["version_distribution"][version] = 0
                stats["version_distribution"][version] += 1

                # Track timestamps
                last_updated = data.get("lastUpdated")
                created_at = data.get("createdAt")

                if last_updated:
                    if not stats["latest_update"] or last_updated > stats["latest_update"]:
                        stats["latest_update"] = last_updated

                if created_at:
                    if not stats["oldest_document"] or created_at < stats["oldest_document"]:
                        stats["oldest_document"] = created_at

            return stats

        except Exception as e:
            logger.error(f"Failed to get metadata statistics: {e}", exc_info=True)
            return {}
