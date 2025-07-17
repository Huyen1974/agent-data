#!/usr/bin/env python3
"""
FAISS to Qdrant Migration Script

This script performs migration from FAISS to Qdrant by:
1. Reading FAISS indexes from GCS (huyen1974-faiss-index-storage-test bucket)
2. Uploading vectors to Qdrant Cloud with timeout/retry logic
3. Logging migration progress and performance metrics
4. Supporting both dry-run and actual migration modes

Usage:
    python scripts/migrate_faiss_to_qdrant.py [--dry-run] [--verbose] [--limit N]
"""

import argparse
import asyncio
import hashlib
import logging
import os
import pickle
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from google.cloud import exceptions as google_cloud_exceptions
from google.cloud import firestore, storage

# Add the project root to the path to import QdrantStore
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_data.vector_store.qdrant_store import QdrantStore  # noqa: E402

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
FAISS_GCS_BUCKET = os.environ.get(
    "GCS_BUCKET_NAME", "huyen1974-faiss-index-storage-test"
)
QDRANT_GCS_BUCKET = os.environ.get("QDRANT_GCS_BUCKET", "qdrant-snapshots")
FIRESTORE_PROJECT_ID = os.environ.get("FIRESTORE_PROJECT_ID", "chatgpt-db-project")
FIRESTORE_DATABASE_ID = os.environ.get("FIRESTORE_DATABASE_ID", "test-default")
FAISS_INDEXES_COLLECTION = os.environ.get(
    "FAISS_INDEXES_COLLECTION", "faiss_indexes_registry"
)

# Qdrant Configuration
QDRANT_URL = os.environ.get(
    "QDRANT_URL",
    "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io",
)
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "migrated_vectors")

# Migration Configuration
# OPTIMIZED FOR QDRANT FREE TIER (CLI 114B7 findings):
# - Concurrency 2: 0.31s/vector (OPTIMAL)
# - Concurrency 3: 0.80s/vector (2.5x slower due to rate limiting)
# - Batch size 100: Optimal balance between throughput and memory
# - Batch delay 3s: Prevents rate limiting on free tier
BATCH_SIZE = 100  # Vectors per batch (20 batches of 100 for 2000 vectors)
BATCH_DELAY = (
    3.0  # Seconds between batches (increased from 2.0 for rate-limit mitigation)
)
TIMEOUT_SECONDS = 30  # Timeout for individual operations
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_DELAY_BASE = 2  # Base delay for exponential backoff
MAX_CONCURRENT_UPLOADS = (
    2  # Maximum concurrent vector uploads (CLI114B7: optimized for Qdrant free tier)
)

# Ensure logs directory exists
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)
MIGRATION_LOG_FILE = LOGS_DIR / "migration.log"
PERF_SLOW_LOG_FILE = LOGS_DIR / "perf_slow.log"


class MigrationError(Exception):
    """Base exception for migration errors"""

    pass


class FAISSIndexNotFoundError(MigrationError):
    """Exception when FAISS index cannot be found or loaded"""

    pass


class ChecksumCalculationError(MigrationError):
    """Exception when checksum calculation fails"""

    pass


class QdrantMigrationError(MigrationError):
    """Exception when Qdrant migration fails"""

    pass


def setup_migration_logger() -> logging.Logger:
    """Setup dedicated logger for migration with file output"""
    migration_logger = logging.getLogger("migration")
    migration_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in migration_logger.handlers[:]:
        migration_logger.removeHandler(handler)

    # File handler for migration log
    file_handler = logging.FileHandler(MIGRATION_LOG_FILE, mode="a")
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    migration_logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(file_formatter)
    migration_logger.addHandler(console_handler)

    return migration_logger


def setup_performance_logger() -> logging.Logger:
    """Setup dedicated logger for performance metrics"""
    perf_logger = logging.getLogger("performance")
    perf_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in perf_logger.handlers[:]:
        perf_logger.removeHandler(handler)

    # File handler for performance log
    file_handler = logging.FileHandler(PERF_SLOW_LOG_FILE, mode="a")
    file_formatter = logging.Formatter(
        "%(asctime)s [%(message)s]", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    perf_logger.addHandler(file_handler)

    return perf_logger


async def retry_with_backoff(
    func, *args, max_retries=MAX_RETRIES, base_delay=RETRY_DELAY_BASE, **kwargs
):
    """Execute function with exponential backoff retry logic"""
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise e

            delay = base_delay * (2**attempt)
            logger.warning(
                f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)


async def upload_vector_with_timeout(
    qdrant_store: QdrantStore,
    point_id: str,
    vector: list[float],
    metadata: dict[str, Any],
    migration_logger: logging.Logger,
    perf_logger: logging.Logger,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Upload a single vector to Qdrant with timeout and performance logging"""
    async with semaphore:  # Control concurrency
        start_time = time.time()

        try:
            # Use asyncio.wait_for to implement timeout
            await asyncio.wait_for(
                retry_with_backoff(
                    qdrant_store.upsert_vector, point_id, vector, metadata
                ),
                timeout=TIMEOUT_SECONDS,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            migration_logger.info(f"[{point_id}] [SUCCESS]")

            # Log slow operations
            if latency_ms > 5000:  # >5 seconds
                perf_logger.info(f"[UPLOAD] [{latency_ms}] [SUCCESS]")

            return True

        except TimeoutError:
            latency_ms = int((time.time() - start_time) * 1000)
            migration_logger.error(f"[{point_id}] [TIMEOUT]")
            perf_logger.info(f"[UPLOAD] [{latency_ms}] [TIMEOUT]")
            return False

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            migration_logger.error(f"[{point_id}] [ERROR: {str(e)}]")
            if latency_ms > 5000:
                perf_logger.info(f"[UPLOAD] [{latency_ms}] [ERROR]")
            return False


def download_gcs_file(
    storage_client: storage.Client,
    bucket_name: str,
    source_blob_name: str,
    destination_file_name: str,
) -> None:
    """Download a file from GCS to local filesystem"""
    logger.info(
        f"Downloading gs://{bucket_name}/{source_blob_name} to {destination_file_name}"
    )

    # Ensure destination directory exists
    os.makedirs(os.path.dirname(destination_file_name), exist_ok=True)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)

    try:
        blob.download_to_filename(destination_file_name)
        logger.info(f"Successfully downloaded {source_blob_name}")
    except google_cloud_exceptions.NotFound:
        raise FAISSIndexNotFoundError(
            f"GCS file not found: gs://{bucket_name}/{source_blob_name}"
        )
    except Exception as e:
        raise MigrationError(f"Failed to download {source_blob_name}: {e}")


def get_faiss_indexes_from_firestore() -> list[dict[str, Any]]:
    """Get list of FAISS indexes from Firestore registry"""
    logger.info(
        f"Querying Firestore for FAISS indexes in collection: {FAISS_INDEXES_COLLECTION}"
    )

    try:
        db = firestore.Client(
            project=FIRESTORE_PROJECT_ID, database=FIRESTORE_DATABASE_ID
        )
        collection_ref = db.collection(FAISS_INDEXES_COLLECTION)
        docs = collection_ref.stream()

        indexes = []
        for doc in docs:
            doc_data = doc.to_dict()
            if doc_data.get("vectorStatus") == "completed":
                indexes.append(
                    {
                        "index_name": doc_data.get("index_name", doc.id),
                        "gcs_faiss_path": doc_data.get("labels", {}).get(
                            "GCSPathIndex"
                        ),
                        "gcs_meta_path": doc_data.get("labels", {}).get("GCSPathMeta"),
                        "vector_count": doc_data.get("labels", {}).get(
                            "VectorCount", 0
                        ),
                        "dimension": doc_data.get("labels", {}).get(
                            "IndexDimension", 0
                        ),
                        "doc_id": doc.id,
                    }
                )

        logger.info(f"Found {len(indexes)} completed FAISS indexes in Firestore")
        return indexes

    except Exception as e:
        raise MigrationError(f"Failed to query Firestore: {e}")


def parse_gcs_path(gcs_path: str) -> tuple[str, str]:
    """Parse GCS path into bucket and blob name"""
    if not gcs_path or not gcs_path.startswith("gs://"):
        raise ValueError(f"Invalid GCS path format: {gcs_path}")

    path_parts = gcs_path[5:].split("/", 1)
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GCS path format: {gcs_path}")

    return path_parts[0], path_parts[1]


def load_faiss_index_and_metadata(
    storage_client: storage.Client,
    gcs_faiss_path: str,
    gcs_meta_path: str,
    temp_dir: str,
) -> tuple[faiss.Index, dict[str, Any], np.ndarray]:
    """Load FAISS index and metadata from GCS"""

    # Parse GCS paths
    faiss_bucket, faiss_blob = parse_gcs_path(gcs_faiss_path)
    meta_bucket, meta_blob = parse_gcs_path(gcs_meta_path)

    # Create temporary file paths
    temp_faiss_path = os.path.join(temp_dir, "temp_index.faiss")
    temp_meta_path = os.path.join(temp_dir, "temp_meta.pkl")

    try:
        # Download FAISS index
        download_gcs_file(storage_client, faiss_bucket, faiss_blob, temp_faiss_path)

        # Download metadata
        download_gcs_file(storage_client, meta_bucket, meta_blob, temp_meta_path)

        # Load FAISS index
        logger.info(f"Loading FAISS index from {temp_faiss_path}")
        index = faiss.read_index(temp_faiss_path)

        # Load metadata
        logger.info(f"Loading metadata from {temp_meta_path}")
        with open(temp_meta_path, "rb") as f:
            metadata = pickle.load(f)

        # Extract vectors from index
        logger.info(f"Extracting {index.ntotal} vectors from FAISS index")
        vectors = np.zeros((index.ntotal, index.d), dtype=np.float32)
        index.reconstruct_n(0, index.ntotal, vectors)

        return index, metadata, vectors

    except Exception as e:
        raise FAISSIndexNotFoundError(f"Failed to load FAISS index: {e}")
    finally:
        # Cleanup temporary files
        for temp_file in [temp_faiss_path, temp_meta_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)


def calculate_vectors_checksum(all_vectors: list[np.ndarray]) -> str:
    """Calculate SHA-256 checksum of all vectors combined"""
    logger.info("Calculating SHA-256 checksum of all vectors")

    try:
        hasher = hashlib.sha256()

        for vectors in all_vectors:
            # Convert to bytes and update hash
            vectors_bytes = vectors.tobytes()
            hasher.update(vectors_bytes)

        checksum = hasher.hexdigest()
        logger.info(f"Calculated checksum: {checksum}")
        return checksum

    except Exception as e:
        raise ChecksumCalculationError(f"Failed to calculate checksum: {e}")


def perform_migration_dryrun(verbose: bool = False) -> dict[str, Any]:
    """Perform dry-run migration analysis"""
    migration_logger = setup_migration_logger()
    start_time = time.time()

    migration_logger.info("=" * 60)
    migration_logger.info("FAISS to Qdrant Migration Dry-Run Started")
    migration_logger.info("=" * 60)

    try:
        # Initialize GCS client
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)

        # Get FAISS indexes from Firestore
        indexes = get_faiss_indexes_from_firestore()

        if not indexes:
            migration_logger.warning("No FAISS indexes found in Firestore registry")
            return {
                "status": "completed",
                "total_indexes": 0,
                "total_vectors": 0,
                "checksum": "",
                "duration_seconds": time.time() - start_time,
            }

        total_vectors = 0
        total_indexes = len(indexes)
        all_vectors = []
        index_details = []

        # Process each index
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, index_info in enumerate(indexes, 1):
                index_name = index_info["index_name"]
                migration_logger.info(
                    f"Processing index {i}/{total_indexes}: {index_name}"
                )

                try:
                    # Load index and extract vectors
                    index, metadata, vectors = load_faiss_index_and_metadata(
                        storage_client,
                        index_info["gcs_faiss_path"],
                        index_info["gcs_meta_path"],
                        temp_dir,
                    )

                    # Collect statistics
                    index_vector_count = index.ntotal
                    index_dimension = index.d
                    total_vectors += index_vector_count
                    all_vectors.append(vectors)

                    index_details.append(
                        {
                            "name": index_name,
                            "vector_count": index_vector_count,
                            "dimension": index_dimension,
                            "metadata_keys": (
                                len(metadata.get("ids", []))
                                if isinstance(metadata, dict)
                                else 0
                            ),
                        }
                    )

                    migration_logger.info(
                        f"Index {index_name}: {index_vector_count} vectors, "
                        f"dimension {index_dimension}"
                    )

                    if verbose:
                        migration_logger.info(f"Metadata structure: {type(metadata)}")
                        if isinstance(metadata, dict):
                            migration_logger.info(
                                f"Metadata keys: {list(metadata.keys())}"
                            )

                except Exception as e:
                    migration_logger.error(f"Failed to process index {index_name}: {e}")
                    # Continue with other indexes
                    continue

        # Calculate overall checksum
        checksum = calculate_vectors_checksum(all_vectors) if all_vectors else ""

        # Log summary
        duration = time.time() - start_time
        migration_logger.info("=" * 60)
        migration_logger.info("MIGRATION DRY-RUN SUMMARY")
        migration_logger.info("=" * 60)
        migration_logger.info(
            f"Total indexes processed: {len(index_details)}/{total_indexes}"
        )
        migration_logger.info(f"Total vectors: {total_vectors}")
        migration_logger.info(f"Data integrity checksum: {checksum}")
        migration_logger.info(f"Duration: {duration:.2f} seconds")

        if verbose and index_details:
            migration_logger.info("\nIndex Details:")
            for detail in index_details:
                migration_logger.info(
                    f"  {detail['name']}: {detail['vector_count']} vectors, "
                    f"dim {detail['dimension']}, {detail['metadata_keys']} metadata entries"
                )

        # Log in required format for verification
        status = "success" if len(index_details) == total_indexes else "partial_success"
        migration_logger.info(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{total_vectors}] [{checksum}] [{status}]"
        )

        return {
            "status": status,
            "total_indexes": total_indexes,
            "processed_indexes": len(index_details),
            "total_vectors": total_vectors,
            "checksum": checksum,
            "duration_seconds": duration,
            "index_details": index_details,
        }

    except Exception as e:
        duration = time.time() - start_time
        migration_logger.error(f"Migration dry-run failed: {e}")
        migration_logger.info(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [0] [] [error]")

        return {"status": "error", "error": str(e), "duration_seconds": duration}

    finally:
        migration_logger.info("=" * 60)
        migration_logger.info("FAISS to Qdrant Migration Dry-Run Completed")
        migration_logger.info("=" * 60)


async def perform_actual_migration(
    limit: int | None = None,
    verbose: bool = False,
    concurrency_level: int = MAX_CONCURRENT_UPLOADS,
) -> dict[str, Any]:
    """Perform actual migration of vectors from FAISS to Qdrant"""
    migration_logger = setup_migration_logger()
    perf_logger = setup_performance_logger()
    start_time = time.time()

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(concurrency_level)

    migration_logger.info("=" * 60)
    migration_logger.info(
        f"FAISS to Qdrant Migration Started (limit: {limit or 'unlimited'}, concurrency: {concurrency_level})"
    )
    migration_logger.info("=" * 60)

    try:
        # Set up environment variables for QdrantStore
        os.environ["QDRANT_URL"] = QDRANT_URL
        os.environ["QDRANT_COLLECTION_NAME"] = QDRANT_COLLECTION_NAME

        # Initialize QdrantStore
        migration_logger.info("Initializing QdrantStore...")
        qdrant_store = QdrantStore()

        # Health check
        migration_logger.info("Performing Qdrant health check...")
        health_start = time.time()
        is_healthy = await qdrant_store.health_check()
        health_latency = int((time.time() - health_start) * 1000)

        if not is_healthy:
            raise QdrantMigrationError("Qdrant health check failed")

        migration_logger.info(f"Qdrant health check passed ({health_latency}ms)")
        if health_latency > 5000:
            perf_logger.info(f"[HEALTH_CHECK] [{health_latency}] [SUCCESS]")

        # Initialize GCS client
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)

        # Get FAISS indexes from Firestore
        indexes = get_faiss_indexes_from_firestore()

        if not indexes:
            migration_logger.warning("No FAISS indexes found in Firestore registry")
            return {
                "status": "completed",
                "total_indexes": 0,
                "total_vectors": 0,
                "uploaded_vectors": 0,
                "failed_vectors": 0,
                "duration_seconds": time.time() - start_time,
            }

        total_vectors_uploaded = 0
        total_vectors_failed = 0
        total_vectors_processed = 0
        vectors_remaining = limit or float("inf")

        # Process each index
        with tempfile.TemporaryDirectory() as temp_dir:
            for i, index_info in enumerate(indexes, 1):
                if vectors_remaining <= 0:
                    break

                index_name = index_info["index_name"]
                migration_logger.info(
                    f"Processing index {i}/{len(indexes)}: {index_name}"
                )

                try:
                    # Load index and extract vectors
                    index, metadata, vectors = load_faiss_index_and_metadata(
                        storage_client,
                        index_info["gcs_faiss_path"],
                        index_info["gcs_meta_path"],
                        temp_dir,
                    )

                    # Limit vectors if specified
                    vectors_to_process = min(len(vectors), int(vectors_remaining))
                    vectors = vectors[:vectors_to_process]

                    migration_logger.info(
                        f"Migrating {vectors_to_process} vectors from {index_name}"
                    )

                    # Process vectors in batches
                    for batch_start in range(0, len(vectors), BATCH_SIZE):
                        batch_end = min(batch_start + BATCH_SIZE, len(vectors))
                        batch_vectors = vectors[batch_start:batch_end]

                        migration_logger.info(
                            f"Processing batch {batch_start//BATCH_SIZE + 1}: vectors {batch_start}-{batch_end-1}"
                        )

                        # Upload batch
                        batch_tasks = []
                        for j, vector in enumerate(batch_vectors):
                            vector_idx = batch_start + j
                            point_id = str(uuid.uuid4())  # Use proper UUID

                            # Create metadata
                            vector_metadata = {
                                "source_index": index_name,
                                "vector_index": vector_idx,
                                "migration_batch": batch_start // BATCH_SIZE + 1,
                                "tag": f"migrated_{index_name}",
                            }

                            # Add original metadata if available
                            if isinstance(metadata, dict) and "ids" in metadata:
                                if vector_idx < len(metadata["ids"]):
                                    vector_metadata["original_id"] = str(
                                        metadata["ids"][vector_idx]
                                    )

                            task = upload_vector_with_timeout(
                                qdrant_store,
                                point_id,
                                vector.tolist(),
                                vector_metadata,
                                migration_logger,
                                perf_logger,
                                semaphore,
                            )
                            batch_tasks.append(task)

                        # Execute batch upload
                        batch_results = await asyncio.gather(
                            *batch_tasks, return_exceptions=True
                        )

                        # Count results
                        batch_success = sum(
                            1 for result in batch_results if result is True
                        )
                        batch_failed = len(batch_results) - batch_success

                        total_vectors_uploaded += batch_success
                        total_vectors_failed += batch_failed
                        total_vectors_processed += len(batch_results)
                        vectors_remaining -= len(batch_results)

                        migration_logger.info(
                            f"Batch completed: {batch_success} success, {batch_failed} failed"
                        )

                        # Sleep between batches
                        if batch_end < len(vectors):
                            await asyncio.sleep(BATCH_DELAY)

                except Exception as e:
                    migration_logger.error(f"Failed to process index {index_name}: {e}")
                    continue

        # Log summary
        duration = time.time() - start_time
        migration_logger.info("=" * 60)
        migration_logger.info("MIGRATION SUMMARY")
        migration_logger.info("=" * 60)
        migration_logger.info(f"Total vectors processed: {total_vectors_processed}")
        migration_logger.info(
            f"Vectors uploaded successfully: {total_vectors_uploaded}"
        )
        migration_logger.info(f"Vectors failed: {total_vectors_failed}")
        migration_logger.info(
            f"Success rate: {(total_vectors_uploaded/total_vectors_processed*100):.1f}%"
            if total_vectors_processed > 0
            else "N/A"
        )
        migration_logger.info(f"Duration: {duration:.2f} seconds")

        return {
            "status": "success" if total_vectors_failed == 0 else "partial_success",
            "total_vectors": total_vectors_processed,
            "uploaded_vectors": total_vectors_uploaded,
            "failed_vectors": total_vectors_failed,
            "duration_seconds": duration,
        }

    except Exception as e:
        duration = time.time() - start_time
        migration_logger.error(f"Migration failed: {e}")

        return {"status": "error", "error": str(e), "duration_seconds": duration}

    finally:
        migration_logger.info("=" * 60)
        migration_logger.info("FAISS to Qdrant Migration Completed")
        migration_logger.info("=" * 60)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="FAISS to Qdrant Migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Perform dry-run analysis only (default: False)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=2000,
        help="Limit number of vectors to migrate (default: 2000)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=MAX_CONCURRENT_UPLOADS,
        help=f"Number of concurrent uploads (default: {MAX_CONCURRENT_UPLOADS})",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("Starting FAISS to Qdrant migration...")
    print(f"Mode: {'Dry-run' if args.dry_run else 'Actual migration'}")
    print(f"Vector limit: {args.limit}")
    print(f"Concurrency level: {args.concurrency}")
    print(f"FAISS GCS Bucket: {FAISS_GCS_BUCKET}")
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Qdrant Collection: {QDRANT_COLLECTION_NAME}")
    print(f"Firestore Project: {FIRESTORE_PROJECT_ID}")
    print(f"Migration log: {MIGRATION_LOG_FILE}")
    if not args.dry_run:
        print(f"Performance log: {PERF_SLOW_LOG_FILE}")
    print("-" * 60)

    if args.dry_run:
        result = perform_migration_dryrun(verbose=args.verbose)
        print("\nDry-run completed!")
        print(f"Status: {result['status']}")
        if result["status"] != "error":
            print(f"Total vectors: {result['total_vectors']}")
            print(f"Checksum: {result['checksum']}")
        print(f"Duration: {result['duration_seconds']:.2f} seconds")
        print(f"Detailed logs: {MIGRATION_LOG_FILE}")
    else:
        # Run actual migration
        try:
            result = asyncio.run(
                perform_actual_migration(
                    limit=args.limit,
                    verbose=args.verbose,
                    concurrency_level=args.concurrency,
                )
            )
            print("\nMigration completed!")
            print(f"Status: {result['status']}")
            if result["status"] != "error":
                print(f"Vectors processed: {result['total_vectors']}")
                print(f"Vectors uploaded: {result['uploaded_vectors']}")
                print(f"Vectors failed: {result['failed_vectors']}")
                if result["total_vectors"] > 0:
                    success_rate = (
                        result["uploaded_vectors"] / result["total_vectors"]
                    ) * 100
                    print(f"Success rate: {success_rate:.1f}%")
                    avg_time_per_vector = (
                        result["duration_seconds"] / result["total_vectors"]
                    )
                    print(f"Average time per vector: {avg_time_per_vector:.2f}s")
            else:
                print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Duration: {result['duration_seconds']:.2f} seconds")
            print(f"Migration logs: {MIGRATION_LOG_FILE}")
            print(f"Performance logs: {PERF_SLOW_LOG_FILE}")
        except Exception as e:
            print(f"\nMigration failed with exception: {e}")
            sys.exit(1)

    # Exit with appropriate code
    exit_code = 0 if result["status"] in ["success", "completed"] else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
