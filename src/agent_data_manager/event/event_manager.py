"""Event manager for Agent-to-Agent (A2A) communication via Google Cloud Pub/Sub."""

import json
import logging
import asyncio
from typing import Dict, Optional, Any, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from ..config.settings import settings
from ..utils.structured_logger import get_logger

# Import Google Cloud Pub/Sub client
try:
    from google.cloud import pubsub_v1
    from google.cloud.pubsub_v1.publisher.exceptions import MessageTooLargeError
    from google.api_core.exceptions import GoogleAPIError

    PUBSUB_AVAILABLE = True
except ImportError:
    pubsub_v1 = None
    MessageTooLargeError = Exception
    GoogleAPIError = Exception
    PUBSUB_AVAILABLE = False
    logging.warning("Google Cloud Pub/Sub not available. Event publishing will be disabled.")

logger = get_logger(__name__)


class EventManager:
    """Manages Agent-to-Agent event publishing via Google Cloud Pub/Sub with optimizations for concurrent operations."""

    def __init__(self, project_id: Optional[str] = None, topic_name: str = "agent-data-events"):
        """Initialize the event manager.

        Args:
            project_id: Optional Google Cloud project ID. Defaults to settings value.
            topic_name: Pub/Sub topic name for publishing events.
        """
        self.project_id = project_id
        self.topic_name = topic_name
        self.publisher = None
        self.topic_path = None
        self._initialized = False
        self._executor = ThreadPoolExecutor(max_workers=4)  # For concurrent publishing
        self._batch_settings = None

    async def _ensure_initialized(self):
        """Ensure Pub/Sub publisher client is initialized with optimized settings."""
        if self._initialized:
            return

        if not PUBSUB_AVAILABLE:
            logger.warning("Pub/Sub not available, events will not be published")
            return

        try:
            # Get project ID from settings if not provided
            if self.project_id is None:
                firestore_config = settings.get_firestore_config()
                self.project_id = firestore_config.get("project_id")

            if not self.project_id:
                raise ValueError("Project ID is required for Pub/Sub event publishing")

            # Initialize publisher client with optimized batch settings
            batch_settings = pubsub_v1.types.BatchSettings(
                max_messages=100,  # Batch up to 100 messages
                max_bytes=1024 * 1024,  # 1MB max batch size
                max_latency=0.1,  # 100ms max latency
            )

            self.publisher = pubsub_v1.PublisherClient(batch_settings=batch_settings)
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            self._batch_settings = batch_settings

            self._initialized = True
            logger.info(f"EventManager initialized for topic: {self.topic_path} with optimized batch settings")

        except Exception as e:
            logger.error(f"Failed to initialize EventManager: {e}")
            raise

    async def publish_batch_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Publish multiple events in a batch for better performance.

        Args:
            events: List of event dictionaries

        Returns:
            Batch publishing operation result
        """
        if not PUBSUB_AVAILABLE:
            logger.debug("Pub/Sub not available, skipping batch event publishing")
            return {"status": "skipped", "reason": "pubsub_not_available"}

        await self._ensure_initialized()

        if not self.publisher:
            logger.warning("Publisher not initialized, skipping batch event publishing")
            return {"status": "skipped", "reason": "publisher_not_initialized"}

        if not events:
            return {"status": "success", "published_count": 0, "message": "No events to publish"}

        try:
            published_count = 0
            failed_count = 0
            message_ids = []

            # Process events concurrently
            publish_tasks = []
            for event in events:
                task = self._publish_single_event_async(event)
                publish_tasks.append(task)

            # Wait for all publishing tasks to complete
            results = await asyncio.gather(*publish_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    failed_count += 1
                    logger.error(f"Failed to publish event in batch: {result}")
                else:
                    published_count += 1
                    if result.get("message_id"):
                        message_ids.append(result["message_id"])

            logger.info(f"Batch event publishing completed: {published_count} successful, {failed_count} failed")

            return {
                "status": "completed",
                "published_count": published_count,
                "failed_count": failed_count,
                "message_ids": message_ids,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to publish batch events: {e}")
            return {"status": "failed", "error": str(e)}

    async def _publish_single_event_async(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a single event asynchronously.

        Args:
            event_data: Event data dictionary

        Returns:
            Publishing operation result
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.utcnow().isoformat()

            # Convert to JSON bytes
            message_data = json.dumps(event_data).encode("utf-8")

            # Check message size
            if len(message_data) > 10 * 1024 * 1024:  # 10MB limit
                raise MessageTooLargeError("Event message too large")

            # Publish message using executor for non-blocking operation
            loop = asyncio.get_event_loop()
            future = self.publisher.publish(self.topic_path, message_data)
            message_id = await loop.run_in_executor(self._executor, future.result)

            return {
                "status": "success",
                "message_id": message_id,
                "event_type": event_data.get("event_type", "unknown"),
                "timestamp": event_data["timestamp"],
            }

        except MessageTooLargeError as e:
            logger.error(f"Event message too large: {e}")
            return {"status": "failed", "error": "Message too large"}
        except GoogleAPIError as e:
            logger.error(f"Google API error publishing event: {e}")
            return {"status": "failed", "error": f"API error: {str(e)}"}
        except Exception as e:
            logger.error(f"Failed to publish single event: {e}")
            return {"status": "failed", "error": str(e)}

    async def publish_save_document_event(
        self, doc_id: str, metadata: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a save_document event to Pub/Sub topic.

        Args:
            doc_id: Document identifier
            metadata: Optional document metadata
            session_id: Optional session identifier

        Returns:
            Publishing operation result
        """
        if not PUBSUB_AVAILABLE:
            logger.debug("Pub/Sub not available, skipping event publishing")
            return {"status": "skipped", "reason": "pubsub_not_available"}

        await self._ensure_initialized()

        if not self.publisher:
            logger.warning("Publisher not initialized, skipping event publishing")
            return {"status": "skipped", "reason": "publisher_not_initialized"}

        try:
            # Prepare event payload
            event_data = {
                "event_type": "save_document",
                "doc_id": doc_id,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id,
                "metadata": metadata or {},
            }

            # Convert to JSON bytes
            message_data = json.dumps(event_data).encode("utf-8")

            # Publish message
            future = self.publisher.publish(self.topic_path, message_data)
            message_id = future.result()  # Wait for the publish to complete

            logger.info(
                "Published save_document event", doc_id=doc_id, message_id=message_id, event_type="save_document"
            )
            return {
                "status": "success",
                "message_id": message_id,
                "doc_id": doc_id,
                "timestamp": event_data["timestamp"],
            }

        except Exception as e:
            logger.error("Failed to publish save_document event", doc_id=doc_id, error=str(e), exc_info=True)
            return {"status": "failed", "error": str(e), "doc_id": doc_id}

    async def publish_custom_event(
        self, event_type: str, event_data: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a custom event to Pub/Sub topic.

        Args:
            event_type: Type of event (e.g., "document_updated", "session_created")
            event_data: Event-specific data
            session_id: Optional session identifier

        Returns:
            Publishing operation result
        """
        if not PUBSUB_AVAILABLE:
            logger.debug("Pub/Sub not available, skipping event publishing")
            return {"status": "skipped", "reason": "pubsub_not_available"}

        await self._ensure_initialized()

        if not self.publisher:
            logger.warning("Publisher not initialized, skipping event publishing")
            return {"status": "skipped", "reason": "publisher_not_initialized"}

        try:
            # Prepare event payload
            full_event_data = {
                "event_type": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id,
                **event_data,
            }

            # Convert to JSON bytes
            message_data = json.dumps(full_event_data).encode("utf-8")

            # Publish message
            future = self.publisher.publish(self.topic_path, message_data)
            message_id = future.result()  # Wait for the publish to complete

            logger.info(f"Published {event_type} event, message_id: {message_id}")
            return {
                "status": "success",
                "message_id": message_id,
                "event_type": event_type,
                "timestamp": full_event_data["timestamp"],
            }

        except Exception as e:
            logger.error(f"Failed to publish {event_type} event: {e}")
            return {"status": "failed", "error": str(e), "event_type": event_type}

    async def get_topic_info(self) -> Dict[str, Any]:
        """
        Get information about the Pub/Sub topic.

        Returns:
            Topic information or error
        """
        if not PUBSUB_AVAILABLE:
            return {"status": "unavailable", "reason": "pubsub_not_available"}

        await self._ensure_initialized()

        if not self.publisher:
            return {"status": "unavailable", "reason": "publisher_not_initialized"}

        try:
            return {
                "status": "available",
                "project_id": self.project_id,
                "topic_name": self.topic_name,
                "topic_path": self.topic_path,
            }

        except Exception as e:
            logger.error(f"Failed to get topic info: {e}")
            return {"status": "failed", "error": str(e)}


# Global event manager instance
_event_manager: Optional[EventManager] = None


def get_event_manager(project_id: Optional[str] = None, topic_name: str = "agent-data-events") -> EventManager:
    """
    Get or create the global event manager instance.

    Args:
        project_id: Optional Google Cloud project ID
        topic_name: Pub/Sub topic name

    Returns:
        EventManager instance
    """
    global _event_manager

    if _event_manager is None:
        _event_manager = EventManager(project_id, topic_name)

    return _event_manager
