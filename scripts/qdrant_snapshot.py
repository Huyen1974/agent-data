#!/usr/bin/env python3
"""
Qdrant Snapshot and GCS Upload Script

This script creates snapshots of Qdrant collections and uploads them to Google Cloud Storage.
It's designed to run every 6 hours via cron job to maintain regular backups.
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
    """Initialize and return Qdrant client using environment variables."""
    qdrant_url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url:
        raise ValueError("QDRANT_URL environment variable not set")

    logger.info(f"Connecting to Qdrant at: {qdrant_url}")
    if api_key:
        logger.info("Using API key authentication")
    else:
        logger.warning("No API key provided - using unauthenticated connection")

    return QdrantClient(url=qdrant_url, api_key=api_key, timeout=30)


def create_snapshot(client: QdrantClient, collection_name: str) -> str:
    """Create a snapshot of the specified collection."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"snapshot_{collection_name}_{timestamp}"

    logger.info(
        f"Creating snapshot '{snapshot_name}' for collection '{collection_name}'"
    )

    try:
        # Create snapshot
        snapshot_info = client.create_snapshot(
            collection_name=collection_name, snapshot_name=snapshot_name
        )
        logger.info(f"Snapshot created successfully: {snapshot_info}")
        return snapshot_name
    except Exception as e:
        logger.error(f"Failed to create snapshot: {str(e)}")
        raise


def download_snapshot(
    client: QdrantClient, collection_name: str, snapshot_name: str
) -> str:
    """Download the snapshot to a temporary file and return the file path."""
    # Create temporary file
    temp_dir = tempfile.mkdtemp()
    snapshot_path = os.path.join(temp_dir, f"{snapshot_name}.snapshot")

    logger.info(f"Downloading snapshot to: {snapshot_path}")

    try:
        # Download snapshot
        client.download_snapshot(
            collection_name=collection_name,
            snapshot_name=snapshot_name,
            location=snapshot_path,
        )

        # Verify file exists and has content
        if os.path.exists(snapshot_path) and os.path.getsize(snapshot_path) > 0:
            file_size = os.path.getsize(snapshot_path)
            logger.info(f"Snapshot downloaded successfully. Size: {file_size} bytes")
            return snapshot_path
        else:
            raise FileNotFoundError(
                f"Downloaded snapshot file not found or empty: {snapshot_path}"
            )

    except Exception as e:
        logger.error(f"Failed to download snapshot: {str(e)}")
        # Clean up temp directory on failure
        if os.path.exists(temp_dir):
            import shutil

            shutil.rmtree(temp_dir)
        raise


def upload_to_gcs(
    snapshot_path: str, snapshot_name: str, bucket_name: str = "qdrant-snapshots"
) -> str:
    """Upload the snapshot file to Google Cloud Storage."""
    logger.info(f"Uploading snapshot to GCS bucket: {bucket_name}")

    try:
        # Initialize GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Create blob path with timestamp folder structure
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        blob_name = f"snapshots/{timestamp}/{snapshot_name}.snapshot"
        blob = bucket.blob(blob_name)

        # Upload file
        blob.upload_from_filename(snapshot_path)

        # Verify upload
        blob.reload()
        logger.info(f"Snapshot uploaded successfully to gs://{bucket_name}/{blob_name}")
        logger.info(f"Upload size: {blob.size} bytes")

        return f"gs://{bucket_name}/{blob_name}"

    except Exception as e:
        logger.error(f"Failed to upload to GCS: {str(e)}")
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


def take_and_upload_snapshot() -> dict[str, Any]:
    """
    Main function to take a snapshot and upload it to GCS.

    Returns:
        Dict containing status and details of the operation
    """
    start_time = datetime.utcnow()
    result = {
        "status": "unknown",
        "start_time": start_time.isoformat(),
        "collection_name": None,
        "snapshot_name": None,
        "gcs_path": None,
        "error": None,
        "duration_seconds": None,
    }

    try:
        # Get configuration
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "my_collection")
        result["collection_name"] = collection_name

        logger.info(f"Starting snapshot process for collection: {collection_name}")

        # Initialize Qdrant client
        client = get_qdrant_client()

        # Verify collection exists
        if not client.collection_exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' does not exist")

        # Create snapshot
        snapshot_name = create_snapshot(client, collection_name)
        result["snapshot_name"] = snapshot_name

        # Download snapshot
        snapshot_path = download_snapshot(client, collection_name, snapshot_name)

        try:
            # Upload to GCS
            gcs_path = upload_to_gcs(snapshot_path, snapshot_name)
            result["gcs_path"] = gcs_path

            # Success
            result["status"] = "success"
            logger.info(f"Snapshot process completed successfully: {snapshot_name}")

        finally:
            # Always clean up local file
            cleanup_local_file(snapshot_path)

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"Snapshot process failed: {str(e)}", exc_info=True)

    finally:
        end_time = datetime.utcnow()
        result["end_time"] = end_time.isoformat()
        result["duration_seconds"] = (end_time - start_time).total_seconds()

    return result


if __name__ == "__main__":
    result = take_and_upload_snapshot()
    print(f"Snapshot result: {result}")

    # Exit with appropriate code
    if result["status"] == "success":
        exit(0)
    else:
        exit(1)
