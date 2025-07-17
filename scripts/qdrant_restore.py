#!/usr/bin/env python3
"""
Qdrant Snapshot Restore Script for Cloud Run

This script downloads the latest snapshot from Google Cloud Storage and restores it
to a Qdrant instance on Cloud Run startup. It's designed to run before Qdrant starts
to ensure data is available immediately.
"""

import logging
import os
import tempfile
from datetime import datetime
from typing import Any

from google.cloud import storage
from qdrant_client import QdrantClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_qdrant_client() -> QdrantClient:
    """Initialize and return Qdrant client for local Docker instance."""
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    logger.info(f"Connecting to Qdrant at: {qdrant_url}")

    # For local Docker instance, no API key needed
    return QdrantClient(url=qdrant_url, timeout=60)


def find_latest_snapshot(bucket_name: str = "qdrant-snapshots") -> str | None:
    """Find the latest snapshot in GCS bucket."""
    logger.info(f"Searching for latest snapshot in bucket: {bucket_name}")

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # List all blobs with snapshots/ prefix
        blobs = list(bucket.list_blobs(prefix="snapshots/"))

        if not blobs:
            logger.info("No snapshots found in GCS bucket")
            return None

        # Find the latest blob by creation time
        latest_blob = max(blobs, key=lambda b: b.time_created)

        logger.info(f"Found latest snapshot: {latest_blob.name}")
        logger.info(f"Created: {latest_blob.time_created}")
        logger.info(f"Size: {latest_blob.size} bytes")

        return latest_blob.name

    except Exception as e:
        logger.error(f"Failed to find latest snapshot: {str(e)}")
        raise


def download_snapshot_from_gcs(
    blob_name: str, bucket_name: str = "qdrant-snapshots"
) -> str:
    """Download snapshot from GCS to local temporary file."""
    logger.info(f"Downloading snapshot: {blob_name}")

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        snapshot_filename = os.path.basename(blob_name)
        snapshot_path = os.path.join(temp_dir, snapshot_filename)

        # Download the blob
        blob.download_to_filename(snapshot_path)

        # Verify download
        if os.path.exists(snapshot_path) and os.path.getsize(snapshot_path) > 0:
            file_size = os.path.getsize(snapshot_path)
            logger.info(f"Snapshot downloaded successfully to: {snapshot_path}")
            logger.info(f"Downloaded size: {file_size} bytes")
            return snapshot_path
        else:
            raise FileNotFoundError(
                f"Downloaded snapshot file not found or empty: {snapshot_path}"
            )

    except Exception as e:
        logger.error(f"Failed to download snapshot from GCS: {str(e)}")
        raise


def restore_snapshot_to_qdrant(snapshot_path: str, collection_name: str) -> bool:
    """Restore snapshot to Qdrant collection."""
    logger.info(f"Restoring snapshot to collection: {collection_name}")

    try:
        client = get_qdrant_client()

        # Check if collection already exists
        if client.collection_exists(collection_name):
            logger.info(
                f"Collection '{collection_name}' already exists, deleting it first"
            )
            client.delete_collection(collection_name)

        # Restore snapshot
        client.restore_snapshot(collection_name=collection_name, location=snapshot_path)

        # Verify restoration
        if client.collection_exists(collection_name):
            collection_info = client.get_collection(collection_name)
            logger.info(
                f"Snapshot restored successfully to collection '{collection_name}'"
            )
            logger.info(f"Collection info: {collection_info}")
            return True
        else:
            logger.error(f"Collection '{collection_name}' not found after restoration")
            return False

    except Exception as e:
        logger.error(f"Failed to restore snapshot: {str(e)}")
        raise


def cleanup_local_file(file_path: str):
    """Clean up the local snapshot file and its directory."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up local file: {file_path}")

            # Also remove the temp directory if it's empty
            temp_dir = os.path.dirname(file_path)
            if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                os.rmdir(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")

    except Exception as e:
        logger.warning(f"Failed to clean up local file {file_path}: {str(e)}")


def download_and_restore_snapshot() -> dict[str, Any]:
    """
    Main function to download and restore the latest snapshot from GCS.

    Returns:
        Dict containing status and details of the operation
    """
    start_time = datetime.utcnow()
    result = {
        "status": "unknown",
        "start_time": start_time.isoformat(),
        "collection_name": None,
        "snapshot_name": None,
        "error": None,
        "duration_seconds": None,
    }

    snapshot_path = None

    try:
        # Get configuration
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "my_collection")
        bucket_name = os.getenv("GCS_BUCKET_NAME", "qdrant-snapshots")

        result["collection_name"] = collection_name

        logger.info(
            f"Starting snapshot restore process for collection: {collection_name}"
        )
        logger.info(f"Using GCS bucket: {bucket_name}")

        # Find latest snapshot
        latest_snapshot_blob = find_latest_snapshot(bucket_name)

        if not latest_snapshot_blob:
            result["status"] = "skipped"
            logger.info("No snapshot found to restore")
            return result

        result["snapshot_name"] = latest_snapshot_blob

        # Download snapshot
        snapshot_path = download_snapshot_from_gcs(latest_snapshot_blob, bucket_name)

        # Restore snapshot
        restore_success = restore_snapshot_to_qdrant(snapshot_path, collection_name)

        if restore_success:
            result["status"] = "success"
            logger.info(
                f"Snapshot restore completed successfully: {latest_snapshot_blob}"
            )
        else:
            result["status"] = "failed"
            result["error"] = "Restoration verification failed"

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"Snapshot restore process failed: {str(e)}", exc_info=True)

    finally:
        # Always clean up local file
        if snapshot_path:
            cleanup_local_file(snapshot_path)

        end_time = datetime.utcnow()
        result["end_time"] = end_time.isoformat()
        result["duration_seconds"] = (end_time - start_time).total_seconds()

    return result


if __name__ == "__main__":
    result = download_and_restore_snapshot()
    print(f"Snapshot restore result: {result}")

    # Exit with appropriate code
    if result["status"] in ["success", "skipped"]:
        exit(0)
    else:
        exit(1)
