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
                f"Failed to initialize Firestore AsyncClient for project '{self.project_id}': {e}",
                exc_info=True,
            )
            # Depending on the application's needs, you might re-raise or handle this.
            # For now, if the client fails to initialize, subsequent operations will fail.
            self.db = None  # Ensure db is None if initialization fails
            raise ConnectionError(f"Could not connect to Firestore: {e}")

    async def save_metadata(self, point_id: Union[str, int], metadata: Dict[str, Any]) -> None:
        """
        Saves or updates metadata for a given point_id in Firestore with versioning support.

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
            # Get existing document to handle versioning
            existing_doc = await doc_ref.get()

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
                f"Successfully saved metadata for point_id '{doc_id}' in Firestore collection '{self.collection_name}' with version {versioned_metadata.get('version', 1)}."
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

        # Apply auto-tagging if content is provided
        if "content" in metadata and metadata["content"]:
            try:
                versioned_metadata = await self._apply_auto_tagging(versioned_metadata)
            except Exception as e:
                logger.warning(f"Failed to apply auto-tagging: {e}")

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

        # Check for modified and added fields
        for key, new_value in new_data.items():
            if key in ["version", "lastUpdated", "version_history"]:
                continue  # Skip versioning fields

            if key not in old_data:
                # Field is new
                changes.append(f"added:{key}")
            else:
                # Field exists, check if modified
                old_value = old_data.get(key)
                if old_value != new_value:
                    changes.append(f"modified:{key}")

        # Check for removed fields
        for key in old_data.keys():
            if key not in new_data and key not in ["version", "lastUpdated", "version_history"]:
                changes.append(f"removed:{key}")

        return changes

    async def _apply_auto_tagging(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply auto-tagging to metadata using LLM.

        Args:
            metadata: Metadata dictionary containing content

        Returns:
            Enhanced metadata with auto-generated tags
        """
        try:
            # Import here to avoid circular imports
            from ..tools.auto_tagging_tool import get_auto_tagging_tool

            auto_tagging_tool = get_auto_tagging_tool()

            # Extract content and existing metadata
            content = metadata.get("content", "")
            if not content:
                return metadata

            # Generate auto-tags
            tag_result = await auto_tagging_tool.generate_tags(
                content=content, existing_metadata=metadata, max_tags=5, use_cache=True
            )

            if tag_result.get("status") == "success":
                tags = tag_result.get("tags", [])

                # Add auto-generated tags to metadata
                metadata["auto_tags"] = tags
                metadata["auto_tag_metadata"] = {
                    "generated_at": tag_result.get("metadata", {}).get("generated_at"),
                    "source": tag_result.get("source"),
                    "content_hash": tag_result.get("content_hash"),
                    "tag_count": len(tags),
                }

                # Merge with existing labels field
                existing_labels = metadata.get("labels", [])
                if isinstance(existing_labels, str):
                    existing_labels = [existing_labels]
                elif not isinstance(existing_labels, list):
                    existing_labels = []

                # Combine labels (remove duplicates)
                all_labels = list(set(existing_labels + tags))
                metadata["labels"] = all_labels

                # Update hierarchy level_2_category if not set and we have auto-tags
                if not metadata.get("level_2_category") and tags:
                    metadata["level_2_category"] = tags[0]

                logger.debug(f"Applied auto-tagging: {len(tags)} tags generated")

            return metadata

        except Exception as e:
            logger.error(f"Auto-tagging failed: {e}")
            return metadata

    def _ensure_hierarchical_structure(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure metadata has hierarchical structure with level_1 through level_6.

        Args:
            metadata: Metadata dictionary

        Returns:
            Metadata with hierarchical structure
        """
        # Initialize hierarchy levels if not present
        hierarchy_levels = [
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "level_4_category",
            "level_5_category",
            "level_6_category",
        ]

        for level in hierarchy_levels:
            if level not in metadata:
                metadata[level] = None

        # Auto-populate hierarchy based on existing metadata with intelligent mapping
        if metadata.get("level_1_category") is None:
            # Try to infer level_1 from document type or category
            if "doc_type" in metadata:
                metadata["level_1_category"] = metadata["doc_type"]
            elif "category" in metadata:
                metadata["level_1_category"] = metadata["category"]
            elif "source" in metadata:
                metadata["level_1_category"] = metadata["source"]
            elif metadata.get("auto_tags"):
                # Use first auto-tag as category if available
                metadata["level_1_category"] = metadata["auto_tags"][0]
            else:
                metadata["level_1_category"] = "document"

        if metadata.get("level_2_category") is None:
            # Try tag, then auto_tags, then subdomain
            if "tag" in metadata:
                metadata["level_2_category"] = metadata["tag"]
            elif metadata.get("auto_tags") and len(metadata["auto_tags"]) > 1:
                metadata["level_2_category"] = metadata["auto_tags"][1]
            elif "subdomain" in metadata:
                metadata["level_2_category"] = metadata["subdomain"]

        if metadata.get("level_3_category") is None:
            # Try author, then project, then third auto-tag
            if "author" in metadata:
                metadata["level_3_category"] = metadata["author"]
            elif "project" in metadata:
                metadata["level_3_category"] = metadata["project"]
            elif metadata.get("auto_tags") and len(metadata["auto_tags"]) > 2:
                metadata["level_3_category"] = metadata["auto_tags"][2]

        if metadata.get("level_4_category") is None:
            # Try year, then date, then fourth auto-tag
            if "year" in metadata:
                metadata["level_4_category"] = str(metadata["year"])
            elif "date" in metadata:
                metadata["level_4_category"] = str(metadata["date"])[:4]  # Extract year from date
            elif metadata.get("auto_tags") and len(metadata["auto_tags"]) > 3:
                metadata["level_4_category"] = metadata["auto_tags"][3]

        if metadata.get("level_5_category") is None:
            # Try language, then format, then fifth auto-tag
            if "language" in metadata:
                metadata["level_5_category"] = metadata["language"]
            elif "format" in metadata:
                metadata["level_5_category"] = metadata["format"]
            elif metadata.get("auto_tags") and len(metadata["auto_tags"]) > 4:
                metadata["level_5_category"] = metadata["auto_tags"][4]

        if metadata.get("level_6_category") is None:
            # Try format, status, or use "general"
            if "format" in metadata and metadata.get("level_5_category") != metadata["format"]:
                metadata["level_6_category"] = metadata["format"]
            elif "status" in metadata:
                metadata["level_6_category"] = metadata["status"]
            elif "priority" in metadata:
                metadata["level_6_category"] = metadata["priority"]
            else:
                metadata["level_6_category"] = "general"

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
                    if level in [
                        "level_1_category",
                        "level_2_category",
                        "level_3_category",
                        "level_4_category",
                        "level_5_category",
                        "level_6_category",
                    ]:
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
        for level in [
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "level_4_category",
            "level_5_category",
            "level_6_category",
        ]:
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
            logger.error(
                f"Failed to delete metadata for point_id '{doc_id}' from Firestore: {e}",
                exc_info=True,
            )
            # Optionally re-raise or handle
            raise

    async def batch_save_metadata(self, metadata_batch: Dict[Union[str, int], Dict[str, Any]]) -> None:
        """
        Saves or updates a batch of metadata in Firestore using a batch writer with versioning support.
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot batch save metadata.")
            return
        if not metadata_batch:
            logger.info("No metadata provided for batch save.")
            return

        batch = self.db.batch()

        # Process each document for versioning
        for point_id, metadata in metadata_batch.items():
            doc_id = str(point_id)
            doc_ref = self.db.collection(self.collection_name).document(doc_id)

            # Get existing document for versioning (Note: This is not ideal for batch operations
            # but necessary for versioning. Consider using a separate versioning strategy for large batches)
            try:
                existing_doc = await doc_ref.get()
                versioned_metadata = await self._prepare_versioned_metadata(metadata, existing_doc)
                batch.set(doc_ref, versioned_metadata)
            except Exception as e:
                logger.error(f"Failed to prepare versioned metadata for {doc_id}: {e}")
                # Continue with other documents
                continue

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

    async def query_documents_by_timestamp(self, field_name: str, before_timestamp: str) -> List[Dict[str, Any]]:
        """
        Query documents where a timestamp field is before the specified timestamp.

        Args:
            field_name: Name of the timestamp field to query (e.g., 'updated_at', 'lastUpdated')
            before_timestamp: ISO format timestamp string

        Returns:
            List of documents matching the criteria
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot query documents.")
            return []

        try:
            collection_ref = self.db.collection(self.collection_name)
            query = collection_ref.where(field_name, "<", before_timestamp)
            docs = query.stream()

            results = []
            async for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id  # Include document ID for deletion
                results.append(doc_data)

            logger.debug(f"Found {len(results)} documents with {field_name} before {before_timestamp}")
            return results

        except Exception as e:
            logger.error(f"Failed to query documents by timestamp: {e}", exc_info=True)
            return []

    async def delete_documents_by_ids(self, doc_ids: List[str]) -> Dict[str, Any]:
        """
        Delete multiple documents by their IDs.

        Args:
            doc_ids: List of document IDs to delete

        Returns:
            Result dictionary with success/failure counts
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot delete documents.")
            return {"deleted_count": 0, "error_count": len(doc_ids)}

        if not doc_ids:
            return {"deleted_count": 0, "error_count": 0}

        deleted_count = 0
        error_count = 0

        try:
            # Use batch delete for efficiency
            batch = self.db.batch()

            for doc_id in doc_ids:
                doc_ref = self.db.collection(self.collection_name).document(doc_id)
                batch.delete(doc_ref)

            await batch.commit()
            deleted_count = len(doc_ids)
            logger.debug(f"Successfully deleted {deleted_count} documents")

        except Exception as e:
            logger.error(f"Failed to batch delete documents: {e}", exc_info=True)
            error_count = len(doc_ids)

        return {"deleted_count": deleted_count, "error_count": error_count}

    async def get_document_path(self, point_id: Union[str, int]) -> Optional[str]:
        """
        Get the hierarchical path of a document for Tree View copy path functionality.

        Args:
            point_id: Document identifier

        Returns:
            Hierarchical path string (e.g., "level_1_category/level_2_category/.../doc_id") or None if not found
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot get document path.")
            return None

        doc_id = str(point_id)
        doc_ref = self.db.collection(self.collection_name).document(doc_id)

        try:
            doc = await doc_ref.get()
            if not doc.exists:
                logger.warning(f"Document {doc_id} not found for path retrieval.")
                return None

            data = doc.to_dict()

            # Build hierarchical path from level_1 to level_6
            path_components = []
            hierarchy_levels = [
                "level_1_category",
                "level_2_category",
                "level_3_category",
                "level_4_category",
                "level_5_category",
                "level_6_category",
            ]

            for level in hierarchy_levels:
                level_value = data.get(level)
                if level_value and level_value.strip():
                    path_components.append(level_value.strip())
                else:
                    break  # Stop at first empty level to avoid gaps

            # Add document ID at the end
            path_components.append(doc_id)

            # Join with forward slashes to create path
            document_path = "/".join(path_components)

            logger.debug(f"Generated document path for {doc_id}: {document_path}")
            return document_path

        except Exception as e:
            logger.error(f"Failed to get document path for {doc_id}: {e}", exc_info=True)
            return None

    async def share_document(
        self, point_id: Union[str, int], shared_by: Optional[str] = None, expires_days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a shareable link for a document and store metadata in project_tree collection.

        Args:
            point_id: Document identifier
            shared_by: Email of the user sharing the document (defaults to service account)
            expires_days: Number of days until the share link expires (default: 7)

        Returns:
            Dictionary with share_id, share_url, and metadata or None if failed
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot share document.")
            return None

        doc_id = str(point_id)

        # Verify document exists
        doc_ref = self.db.collection(self.collection_name).document(doc_id)
        try:
            doc = await doc_ref.get()
            if not doc.exists:
                logger.warning(f"Document {doc_id} not found for sharing.")
                return None
        except Exception as e:
            logger.error(f"Failed to verify document {doc_id} exists: {e}", exc_info=True)
            return None

        try:
            # Generate unique share ID
            import uuid

            share_id = str(uuid.uuid4())

            # Calculate expiration date
            from datetime import datetime, timedelta

            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(days=expires_days)

            # Default shared_by to service account if not provided
            if not shared_by:
                shared_by = "gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"

            # Prepare share metadata
            share_metadata = {
                "share_id": share_id,
                "doc_id": doc_id,
                "created_at": created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "shared_by": shared_by,
                "access_count": 0,
                "last_accessed": None,
                "status": "active",
            }

            # Store in project_tree collection
            project_tree_ref = self.db.collection("project_tree").document(share_id)
            await project_tree_ref.set(share_metadata)

            # Generate shareable URL
            share_url = f"https://agent-data/share/{share_id}"

            result = {
                "share_id": share_id,
                "share_url": share_url,
                "doc_id": doc_id,
                "created_at": share_metadata["created_at"],
                "expires_at": share_metadata["expires_at"],
                "shared_by": shared_by,
            }

            logger.info(f"Successfully created share link for document {doc_id}: {share_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to create share link for document {doc_id}: {e}", exc_info=True)
            return None

    async def search_by_path(self, path_query: str) -> List[Dict[str, Any]]:
        """
        Search documents by hierarchical path segments for Tree View.

        Args:
            path_query: Path segment to search for (e.g., "research_paper", "machine_learning")

        Returns:
            List of documents matching the path query
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot search by path.")
            return []

        if not path_query or not path_query.strip():
            logger.warning("Empty path query provided.")
            return []

        path_query = path_query.strip().lower()

        try:
            collection_ref = self.db.collection(self.collection_name)
            results = []

            # Search across all hierarchy levels
            hierarchy_levels = [
                "level_1_category",
                "level_2_category",
                "level_3_category",
                "level_4_category",
                "level_5_category",
                "level_6_category",
            ]

            for level in hierarchy_levels:
                # Case-insensitive search using array-contains for partial matches
                query = collection_ref.where(level, ">=", path_query).where(level, "<=", path_query + "\uf8ff")
                docs = query.stream()

                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data["_doc_id"] = doc.id
                    doc_data["_matched_level"] = level

                    # Avoid duplicates
                    if not any(existing["_doc_id"] == doc.id for existing in results):
                        results.append(doc_data)

            logger.debug(f"Found {len(results)} documents matching path query: {path_query}")
            return results

        except Exception as e:
            logger.error(f"Failed to search by path '{path_query}': {e}", exc_info=True)
            return []

    async def search_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """
        Search documents by tags for Tree View.

        Args:
            tags: List of tags to search for

        Returns:
            List of documents containing any of the specified tags
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot search by tags.")
            return []

        if not tags or not any(tag.strip() for tag in tags):
            logger.warning("Empty tags list provided.")
            return []

        # Clean and normalize tags
        clean_tags = [tag.strip().lower() for tag in tags if tag.strip()]

        try:
            collection_ref = self.db.collection(self.collection_name)
            results = []

            # Search in auto_tags field using array-contains-any
            query = collection_ref.where("auto_tags", "array-contains-any", clean_tags)
            docs = query.stream()

            for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id

                # Find matching tags for reference
                doc_tags = doc_data.get("auto_tags", [])
                matched_tags = [tag for tag in doc_tags if tag.lower() in clean_tags]
                doc_data["_matched_tags"] = matched_tags

                results.append(doc_data)

            logger.debug(f"Found {len(results)} documents matching tags: {clean_tags}")
            return results

        except Exception as e:
            logger.error(f"Failed to search by tags {clean_tags}: {e}", exc_info=True)
            return []

    async def search_by_metadata(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search documents by metadata fields for Tree View.

        Args:
            filters: Dictionary of field-value pairs to filter by
                    (e.g., {"author": "John Doe", "year": 2024, "vectorStatus": "completed"})

        Returns:
            List of documents matching the metadata filters
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot search by metadata.")
            return []

        if not filters:
            logger.warning("Empty filters provided.")
            return []

        try:
            collection_ref = self.db.collection(self.collection_name)
            query = collection_ref

            # Apply filters sequentially
            for field, value in filters.items():
                if field and value is not None:
                    # Handle string values with case-insensitive search
                    if isinstance(value, str):
                        value = value.strip()
                        if value:
                            # For exact matches on string fields
                            query = query.where(field, "==", value)
                    else:
                        # For non-string values (numbers, booleans, etc.)
                        query = query.where(field, "==", value)

            docs = query.stream()
            results = []

            for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id
                doc_data["_matched_filters"] = filters
                results.append(doc_data)

            logger.debug(f"Found {len(results)} documents matching metadata filters: {filters}")
            return results

        except Exception as e:
            logger.error(f"Failed to search by metadata {filters}: {e}", exc_info=True)
            return []

    async def query_by_hierarchy_optimized(
        self,
        level_1: Optional[str] = None,
        level_2: Optional[str] = None,
        level_3: Optional[str] = None,
        level_4: Optional[str] = None,
        level_5: Optional[str] = None,
        level_6: Optional[str] = None,
        version_order: str = "desc",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Optimized hierarchical query using indexed fields.

        Args:
            level_1 to level_6: Hierarchy level filters
            version_order: "desc" or "asc" for version ordering
            limit: Maximum number of results

        Returns:
            List of documents matching hierarchy filters, ordered by version
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot query by hierarchy.")
            return []

        try:
            import time

            start_time = time.time()

            collection_ref = self.db.collection(self.collection_name)
            query = collection_ref

            # Apply hierarchy filters in order (leverages composite indexes)
            hierarchy_filters = [
                ("level_1_category", level_1),
                ("level_2_category", level_2),
                ("level_3_category", level_3),
                ("level_4_category", level_4),
                ("level_5_category", level_5),
                ("level_6_category", level_6),
            ]

            active_filters = []
            for field, value in hierarchy_filters:
                if value is not None and value.strip():
                    query = query.where(field, "==", value.strip())
                    active_filters.append(f"{field}={value.strip()}")

            # Add version ordering (leverages indexes)
            if version_order.lower() == "desc":
                query = query.order_by("version", direction="DESCENDING")
            else:
                query = query.order_by("version", direction="ASCENDING")

            # Apply limit
            query = query.limit(limit)

            # Execute query
            docs = query.stream()
            results = []

            async for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id
                results.append(doc_data)

            query_time = time.time() - start_time
            logger.info(
                f"Optimized hierarchy query completed in {query_time:.3f}s, "
                f"filters: [{', '.join(active_filters)}], results: {len(results)}"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to execute optimized hierarchy query: {e}", exc_info=True)
            return []

    async def query_by_version_range_optimized(
        self,
        min_version: Optional[int] = None,
        max_version: Optional[int] = None,
        level_1_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Optimized version range query using indexed fields.

        Args:
            min_version: Minimum version (inclusive)
            max_version: Maximum version (inclusive)
            level_1_filter: Optional level_1_category filter
            limit: Maximum number of results

        Returns:
            List of documents in version range, ordered by version desc
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot query by version range.")
            return []

        try:
            import time

            start_time = time.time()

            collection_ref = self.db.collection(self.collection_name)
            query = collection_ref

            # Apply level_1 filter first if provided (leverages composite index)
            if level_1_filter and level_1_filter.strip():
                query = query.where("level_1_category", "==", level_1_filter.strip())

            # Apply version range filters
            if min_version is not None:
                query = query.where("version", ">=", min_version)
            if max_version is not None:
                query = query.where("version", "<=", max_version)

            # Order by version descending (leverages index)
            query = query.order_by("version", direction="DESCENDING")
            query = query.limit(limit)

            # Execute query
            docs = query.stream()
            results = []

            async for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id
                results.append(doc_data)

            query_time = time.time() - start_time
            filter_desc = f"version: {min_version}-{max_version}"
            if level_1_filter:
                filter_desc += f", level_1: {level_1_filter}"

            logger.info(
                f"Optimized version range query completed in {query_time:.3f}s, "
                f"filters: [{filter_desc}], results: {len(results)}"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to execute optimized version range query: {e}", exc_info=True)
            return []

    async def query_latest_by_category_optimized(
        self, category_level: str = "level_1_category", category_value: str = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Optimized query for latest documents by category using indexed fields.

        Args:
            category_level: Which level to filter by (level_1_category to level_6_category)
            category_value: Value to filter by
            limit: Maximum number of results

        Returns:
            List of latest documents in category, ordered by version desc
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot query latest by category.")
            return []

        valid_levels = [
            "level_1_category",
            "level_2_category",
            "level_3_category",
            "level_4_category",
            "level_5_category",
            "level_6_category",
        ]

        if category_level not in valid_levels:
            logger.error(f"Invalid category_level: {category_level}. Must be one of {valid_levels}")
            return []

        if not category_value or not category_value.strip():
            logger.error("category_value is required")
            return []

        try:
            import time

            start_time = time.time()

            collection_ref = self.db.collection(self.collection_name)

            # Use composite index: category + version
            query = (
                collection_ref.where(category_level, "==", category_value.strip())
                .order_by("version", direction="DESCENDING")
                .limit(limit)
            )

            # Execute query
            docs = query.stream()
            results = []

            async for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id
                results.append(doc_data)

            query_time = time.time() - start_time
            logger.info(
                f"Optimized latest by category query completed in {query_time:.3f}s, "
                f"filter: [{category_level}={category_value}], results: {len(results)}"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to execute optimized latest by category query: {e}", exc_info=True)
            return []

    async def query_multi_level_hierarchy_optimized(
        self,
        level_1: str,
        level_2: Optional[str] = None,
        order_by_updated: bool = True,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Optimized multi-level hierarchy query using composite indexes.

        Args:
            level_1: Required level_1_category filter
            level_2: Optional level_2_category filter
            order_by_updated: If True, order by lastUpdated desc, else by version desc
            limit: Maximum number of results

        Returns:
            List of documents matching hierarchy, ordered as specified
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot query multi-level hierarchy.")
            return []

        if not level_1 or not level_1.strip():
            logger.error("level_1 is required for multi-level hierarchy query")
            return []

        try:
            import time

            start_time = time.time()

            collection_ref = self.db.collection(self.collection_name)
            query = collection_ref.where("level_1_category", "==", level_1.strip())

            if level_2 and level_2.strip():
                query = query.where("level_2_category", "==", level_2.strip())

            # Use appropriate composite index based on ordering preference
            if order_by_updated:
                query = query.order_by("lastUpdated", direction="DESCENDING")
            else:
                query = query.order_by("version", direction="DESCENDING")

            query = query.limit(limit)

            # Execute query
            docs = query.stream()
            results = []

            async for doc in docs:
                doc_data = doc.to_dict()
                doc_data["_doc_id"] = doc.id
                results.append(doc_data)

            query_time = time.time() - start_time
            filter_desc = f"level_1={level_1}"
            if level_2:
                filter_desc += f", level_2={level_2}"
            order_desc = "lastUpdated" if order_by_updated else "version"

            logger.info(
                f"Optimized multi-level hierarchy query completed in {query_time:.3f}s, "
                f"filters: [{filter_desc}], order: {order_desc}, results: {len(results)}"
            )

            return results

        except Exception as e:
            logger.error(f"Failed to execute optimized multi-level hierarchy query: {e}", exc_info=True)
            return []

    async def benchmark_query_performance(self) -> Dict[str, Any]:
        """
        Benchmark the performance of optimized queries.

        Returns:
            Dictionary with performance metrics for different query types
        """
        if not self.db:
            logger.error("Firestore client not initialized. Cannot benchmark queries.")
            return {}

        try:
            import time

            benchmark_results = {"timestamp": time.time(), "queries": {}}

            # Test 1: Simple hierarchy query
            start_time = time.time()
            results1 = await self.query_by_hierarchy_optimized(level_1="document", limit=10)
            benchmark_results["queries"]["hierarchy_simple"] = {
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "result_count": len(results1),
                "query_type": "level_1_category + version order",
            }

            # Test 2: Version range query
            start_time = time.time()
            results2 = await self.query_by_version_range_optimized(min_version=1, max_version=10, limit=10)
            benchmark_results["queries"]["version_range"] = {
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "result_count": len(results2),
                "query_type": "version range + order",
            }

            # Test 3: Latest by category
            start_time = time.time()
            results3 = await self.query_latest_by_category_optimized(
                category_level="level_1_category", category_value="document", limit=10
            )
            benchmark_results["queries"]["latest_by_category"] = {
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "result_count": len(results3),
                "query_type": "category + version order",
            }

            # Test 4: Multi-level hierarchy
            start_time = time.time()
            results4 = await self.query_multi_level_hierarchy_optimized(level_1="document", level_2=None, limit=10)
            benchmark_results["queries"]["multi_level_hierarchy"] = {
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "result_count": len(results4),
                "query_type": "level_1 + level_2 + lastUpdated order",
            }

            # Calculate summary statistics
            durations = [q["duration_ms"] for q in benchmark_results["queries"].values()]
            benchmark_results["summary"] = {
                "total_queries": len(durations),
                "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "all_under_2000ms": all(d < 2000 for d in durations),
            }

            logger.info(
                f"Query performance benchmark completed: "
                f"avg={benchmark_results['summary']['avg_duration_ms']}ms, "
                f"max={benchmark_results['summary']['max_duration_ms']}ms"
            )

            return benchmark_results

        except Exception as e:
            logger.error(f"Failed to benchmark query performance: {e}", exc_info=True)
            return {"error": str(e), "timestamp": time.time()}
