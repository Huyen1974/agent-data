"""Session memory manager for Agent Data system using Firestore."""

import uuid
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from ..config.settings import settings
from ..vector_store.firestore_metadata_manager import FirestoreMetadataManager
from ..utils.structured_logger import get_logger

# Import Firestore for optimistic locking
try:
    from google.cloud import firestore
    from google.cloud.firestore_v1.base_query import FieldFilter

    FIRESTORE_AVAILABLE = True
except ImportError:
    firestore = None
    FieldFilter = None
    FIRESTORE_AVAILABLE = False

logger = get_logger(__name__)


class ConcurrentUpdateError(Exception):
    """Raised when concurrent update conflicts occur"""

    pass


class SessionManager:
    """Manages session memory using Firestore agent_sessions collection with optimistic locking for concurrent operations."""

    def __init__(self, project_id: Optional[str] = None):
        """Initialize the session manager.

        Args:
            project_id: Optional Firestore project ID. Defaults to settings value.
        """
        self.firestore_manager = None
        self._initialized = False
        self.project_id = project_id
        self._max_retry_attempts = 3

    async def _ensure_initialized(self):
        """Ensure FirestoreMetadataManager is initialized for agent_sessions collection."""
        if self._initialized:
            return

        try:
            firestore_config = settings.get_firestore_config()
            self.firestore_manager = FirestoreMetadataManager(
                project_id=self.project_id or firestore_config.get("project_id"),
                collection_name="agent_sessions",
            )
            self._initialized = True
            logger.info("SessionManager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize SessionManager: {e}")
            raise

    async def create_session(
        self, session_id: Optional[str] = None, initial_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new session with optional initial state.

        Args:
            session_id: Optional session ID. If not provided, a UUID will be generated.
            initial_state: Optional initial state dictionary.

        Returns:
            Session creation result with session_id and status
        """
        await self._ensure_initialized()

        try:
            # Generate session ID if not provided
            if session_id is None:
                session_id = str(uuid.uuid4())

            # Prepare session data with version for optimistic locking
            session_data = {
                "session_id": session_id,
                "state": initial_state or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "status": "active",
                "version": 1,  # Start with version 1 for optimistic locking
                "lock_timestamp": None,  # For detecting stale locks
            }

            # Save to Firestore
            await self.firestore_manager.save_metadata(session_id, session_data)

            logger.info("Created session", session_id=session_id, status="active", version=1)
            return {
                "status": "success",
                "session_id": session_id,
                "created_at": session_data["created_at"],
                "version": 1,
            }

        except Exception as e:
            logger.error("Failed to create session", error=str(e), exc_info=True)
            return {"status": "failed", "error": str(e)}

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data by session ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        await self._ensure_initialized()

        try:
            session_data = await self.firestore_manager.get_metadata(session_id)
            if session_data:
                logger.debug(f"Retrieved session: {session_id}")
                return session_data
            else:
                logger.debug(f"Session not found: {session_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def update_session_state_with_optimistic_locking(
        self, session_id: str, state_update: Dict[str, Any], expected_version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update session state with optimistic locking to handle concurrent operations.

        Args:
            session_id: Session identifier
            state_update: State updates to merge
            expected_version: Expected version for optimistic locking

        Returns:
            Update operation result
        """
        await self._ensure_initialized()

        for attempt in range(self._max_retry_attempts):
            try:
                # Get existing session with current version
                existing_session = await self.get_session(session_id)
                if not existing_session:
                    return {"status": "failed", "error": f"Session {session_id} not found"}

                current_version = existing_session.get("version", 1)

                # Check version conflict if expected_version is provided
                if expected_version is not None and current_version != expected_version:
                    raise ConcurrentUpdateError(
                        f"Version conflict: expected {expected_version}, current {current_version}"
                    )

                # Check for stale locks (older than 30 seconds)
                lock_timestamp = existing_session.get("lock_timestamp")
                if lock_timestamp:
                    lock_time = datetime.fromisoformat(lock_timestamp.replace("Z", "+00:00"))
                    if (datetime.utcnow() - lock_time.replace(tzinfo=None)).total_seconds() > 30:
                        logger.warning(f"Detected stale lock for session {session_id}, proceeding with update")

                # Merge state updates
                current_state = existing_session.get("state", {}).copy()
                current_state.update(state_update)

                # Update session data with new version
                updated_data = existing_session.copy()
                updated_data["state"] = current_state
                updated_data["updated_at"] = datetime.utcnow().isoformat()
                updated_data["version"] = current_version + 1
                updated_data["lock_timestamp"] = None  # Clear lock

                # Save updated session
                await self.firestore_manager.save_metadata(session_id, updated_data)

                logger.debug(
                    f"Updated session state: {session_id}, version: {current_version} -> {current_version + 1}"
                )
                return {
                    "status": "success",
                    "session_id": session_id,
                    "updated_at": updated_data["updated_at"],
                    "version": current_version + 1,
                }

            except ConcurrentUpdateError as e:
                if attempt < self._max_retry_attempts - 1:
                    # Wait with exponential backoff before retry
                    wait_time = 0.1 * (2**attempt)
                    await asyncio.sleep(wait_time)
                    logger.warning(f"Concurrent update conflict for session {session_id}, retrying in {wait_time}s")
                    continue
                else:
                    logger.error(f"Failed to update session state after {self._max_retry_attempts} attempts: {e}")
                    return {"status": "failed", "error": f"Concurrent update conflict: {str(e)}"}
            except Exception as e:
                logger.error(f"Failed to update session state {session_id}: {e}")
                return {"status": "failed", "error": str(e)}

        return {"status": "failed", "error": "Max retry attempts exceeded"}

    async def update_session_state(self, session_id: str, state_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update session state by merging with existing state (backward compatibility method).

        Args:
            session_id: Session identifier
            state_update: State updates to merge

        Returns:
            Update operation result
        """
        return await self.update_session_state_with_optimistic_locking(session_id, state_update)

    async def acquire_session_lock(self, session_id: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        """
        Acquire a lock on a session for exclusive access.

        Args:
            session_id: Session identifier
            timeout_seconds: Lock timeout in seconds

        Returns:
            Lock acquisition result
        """
        await self._ensure_initialized()

        try:
            existing_session = await self.get_session(session_id)
            if not existing_session:
                return {"status": "failed", "error": f"Session {session_id} not found"}

            # Check if already locked
            lock_timestamp = existing_session.get("lock_timestamp")
            if lock_timestamp:
                lock_time = datetime.fromisoformat(lock_timestamp.replace("Z", "+00:00"))
                if (datetime.utcnow() - lock_time.replace(tzinfo=None)).total_seconds() < timeout_seconds:
                    return {"status": "failed", "error": "Session is already locked"}

            # Acquire lock
            updated_data = existing_session.copy()
            updated_data["lock_timestamp"] = datetime.utcnow().isoformat()
            updated_data["updated_at"] = datetime.utcnow().isoformat()

            await self.firestore_manager.save_metadata(session_id, updated_data)

            logger.debug(f"Acquired lock for session: {session_id}")
            return {"status": "success", "session_id": session_id, "lock_acquired_at": updated_data["lock_timestamp"]}

        except Exception as e:
            logger.error(f"Failed to acquire lock for session {session_id}: {e}")
            return {"status": "failed", "error": str(e)}

    async def release_session_lock(self, session_id: str) -> Dict[str, Any]:
        """
        Release a lock on a session.

        Args:
            session_id: Session identifier

        Returns:
            Lock release result
        """
        await self._ensure_initialized()

        try:
            existing_session = await self.get_session(session_id)
            if not existing_session:
                return {"status": "failed", "error": f"Session {session_id} not found"}

            # Release lock
            updated_data = existing_session.copy()
            updated_data["lock_timestamp"] = None
            updated_data["updated_at"] = datetime.utcnow().isoformat()

            await self.firestore_manager.save_metadata(session_id, updated_data)

            logger.debug(f"Released lock for session: {session_id}")
            return {"status": "success", "session_id": session_id, "lock_released_at": updated_data["updated_at"]}

        except Exception as e:
            logger.error(f"Failed to release lock for session {session_id}: {e}")
            return {"status": "failed", "error": str(e)}

    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete a session from Firestore.

        Args:
            session_id: Session identifier

        Returns:
            Delete operation result
        """
        await self._ensure_initialized()

        try:
            await self.firestore_manager.delete_metadata(session_id)
            logger.info(f"Deleted session: {session_id}")
            return {"status": "success", "session_id": session_id}

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return {"status": "failed", "error": str(e)}

    async def list_sessions(self, limit: int = 50) -> Dict[str, Any]:
        """
        List all sessions with optional limit.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of sessions and count
        """
        await self._ensure_initialized()

        try:
            # Use the statistics method to get session info
            stats = await self.firestore_manager.get_metadata_statistics()

            # For a more detailed list, we'd need to implement a list method in FirestoreMetadataManager
            # For now, return basic statistics
            return {
                "status": "success",
                "total_sessions": stats.get("total_documents", 0),
                "latest_update": stats.get("latest_update"),
                "oldest_session": stats.get("oldest_document"),
            }

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return {"status": "failed", "error": str(e)}

    async def clear_expired_sessions(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """
        Clear sessions older than specified hours.

        Args:
            max_age_hours: Maximum age in hours before session is considered expired

        Returns:
            Cleanup operation result
        """
        await self._ensure_initialized()

        try:
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            cutoff_iso = cutoff_time.isoformat()

            logger.info(f"Starting expired session cleanup (max_age: {max_age_hours}h, cutoff: {cutoff_iso})")

            # Query for expired sessions using the new timestamp query method
            expired_sessions = await self.firestore_manager.query_documents_by_timestamp(
                field_name="updated_at", before_timestamp=cutoff_iso
            )

            if not expired_sessions:
                logger.info("No expired sessions found")
                return {
                    "status": "success",
                    "deleted_count": 0,
                    "error_count": 0,
                    "cutoff_time": cutoff_iso,
                    "max_age_hours": max_age_hours,
                }

            # Extract document IDs for deletion
            doc_ids_to_delete = [session.get("_doc_id") for session in expired_sessions if session.get("_doc_id")]

            if not doc_ids_to_delete:
                logger.warning("Found expired sessions but no valid document IDs")
                return {
                    "status": "success",
                    "deleted_count": 0,
                    "error_count": 0,
                    "cutoff_time": cutoff_iso,
                    "max_age_hours": max_age_hours,
                }

            # Delete expired sessions
            delete_result = await self.firestore_manager.delete_documents_by_ids(doc_ids_to_delete)

            deleted_count = delete_result.get("deleted_count", 0)
            error_count = delete_result.get("error_count", 0)

            logger.info(f"Expired session cleanup completed. Deleted: {deleted_count}, Errors: {error_count}")

            return {
                "status": "success",
                "deleted_count": deleted_count,
                "error_count": error_count,
                "cutoff_time": cutoff_iso,
                "max_age_hours": max_age_hours,
                "expired_sessions_found": len(expired_sessions),
            }

        except Exception as e:
            logger.error(f"Failed to clear expired sessions: {e}")
            return {"status": "failed", "error": str(e)}


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(project_id: Optional[str] = None) -> SessionManager:
    """
    Get or create the global session manager instance.

    Args:
        project_id: Optional Firestore project ID

    Returns:
        SessionManager instance
    """
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager(project_id)

    return _session_manager
