#!/usr/bin/env python3
"""
Generate Sample Data for FAISS to Qdrant Migration Testing

This script generates ~10k vector samples with metadata, stores them in a FAISS index,
uploads to GCS, and registers in Firestore for migration testing.

Usage:
    python scripts/generate_sample_data.py [--vector-count 10000] [--dimension 1536]
"""

import os
import sys
import time
import pickle
import logging
import argparse
import tempfile
from typing import Dict, List, Any

import numpy as np
import faiss
from google.cloud import storage, firestore

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
FAISS_GCS_BUCKET = os.environ.get("GCS_BUCKET_NAME", "huyen1974-faiss-index-storage-test")
FIRESTORE_PROJECT_ID = os.environ.get("FIRESTORE_PROJECT_ID", "chatgpt-db-project")
FIRESTORE_DATABASE_ID = os.environ.get("FIRESTORE_DATABASE_ID", "test-default")
FAISS_INDEXES_COLLECTION = os.environ.get("FAISS_INDEXES_COLLECTION", "faiss_indexes_registry")


def generate_sample_vectors(count: int, dimension: int) -> tuple[np.ndarray, List[Dict[str, Any]]]:
    """Generate sample vectors and metadata"""
    logger.info(f"Generating {count} sample vectors with dimension {dimension}")

    # Generate random vectors (normalized for better similarity search)
    vectors = np.random.randn(count, dimension).astype(np.float32)
    # Normalize vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms

    # Generate metadata for each vector
    metadata = []
    for i in range(count):
        metadata.append(
            {
                "id": f"sample_vector_{i:06d}",
                "text": f"This is sample text content for vector {i}",
                "category": f"category_{i % 10}",  # 10 different categories
                "timestamp": int(time.time()) + i,
                "source": "sample_data_generator",
                "batch_id": i // 1000,  # Group into batches of 1000
            }
        )

    logger.info(f"Generated {len(vectors)} vectors and {len(metadata)} metadata entries")
    return vectors, metadata


def create_faiss_index(vectors: np.ndarray, metadata: List[Dict[str, Any]]) -> tuple[faiss.Index, Dict[str, Any]]:
    """Create FAISS index with vectors and prepare metadata"""
    logger.info(f"Creating FAISS index for {len(vectors)} vectors")

    # Create FAISS index (using IndexFlatIP for inner product similarity)
    dimension = vectors.shape[1]
    index = faiss.IndexFlatIP(dimension)

    # Add vectors to index
    index.add(vectors)

    # Prepare metadata structure
    metadata_dict = {
        "ids": [meta["id"] for meta in metadata],
        "texts": [meta["text"] for meta in metadata],
        "metadata": metadata,
        "index_info": {
            "total_vectors": len(vectors),
            "dimension": dimension,
            "index_type": "IndexFlatIP",
            "created_at": int(time.time()),
        },
    }

    logger.info(f"Created FAISS index with {index.ntotal} vectors")
    return index, metadata_dict


def upload_to_gcs(storage_client: storage.Client, bucket_name: str, local_file: str, gcs_path: str) -> str:
    """Upload file to GCS and return full GCS path"""
    logger.info(f"Uploading {local_file} to gs://{bucket_name}/{gcs_path}")

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)

    blob.upload_from_filename(local_file)

    full_path = f"gs://{bucket_name}/{gcs_path}"
    logger.info(f"Successfully uploaded to {full_path}")
    return full_path


def register_in_firestore(
    index_name: str, gcs_faiss_path: str, gcs_meta_path: str, vector_count: int, dimension: int
) -> str:
    """Register the index in Firestore"""
    logger.info(f"Registering index {index_name} in Firestore")

    db = firestore.Client(project=FIRESTORE_PROJECT_ID, database=FIRESTORE_DATABASE_ID)
    collection_ref = db.collection(FAISS_INDEXES_COLLECTION)

    doc_data = {
        "index_name": index_name,
        "vectorStatus": "completed",
        "labels": {
            "GCSPathIndex": gcs_faiss_path,
            "GCSPathMeta": gcs_meta_path,
            "VectorCount": vector_count,
            "IndexDimension": dimension,
            "CreatedBy": "sample_data_generator",
            "CreatedAt": int(time.time()),
        },
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
    }

    doc_ref = collection_ref.document(index_name)
    doc_ref.set(doc_data)

    logger.info(f"Registered index {index_name} in Firestore collection {FAISS_INDEXES_COLLECTION}")
    return doc_ref.id


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate Sample Data for FAISS Migration")
    parser.add_argument(
        "--vector-count", type=int, default=10000, help="Number of vectors to generate (default: 10000)"
    )
    parser.add_argument("--dimension", type=int, default=1536, help="Vector dimension (default: 1536)")
    parser.add_argument(
        "--index-name",
        type=str,
        default="sample_migration_test",
        help="Name for the FAISS index (default: sample_migration_test)",
    )

    args = parser.parse_args()

    print("Generating sample data for FAISS to Qdrant migration...")
    print(f"Vector count: {args.vector_count}")
    print(f"Dimension: {args.dimension}")
    print(f"Index name: {args.index_name}")
    print(f"GCS Bucket: {FAISS_GCS_BUCKET}")
    print("-" * 60)

    try:
        # Generate sample data
        vectors, metadata = generate_sample_vectors(args.vector_count, args.dimension)

        # Create FAISS index
        index, metadata_dict = create_faiss_index(vectors, metadata)

        # Initialize GCS client
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)

        # Create temporary files and upload to GCS
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save FAISS index
            faiss_file = os.path.join(temp_dir, f"{args.index_name}.faiss")
            faiss.write_index(index, faiss_file)

            # Save metadata
            meta_file = os.path.join(temp_dir, f"{args.index_name}_meta.pkl")
            with open(meta_file, "wb") as f:
                pickle.dump(metadata_dict, f)

            # Upload to GCS
            gcs_faiss_path = upload_to_gcs(
                storage_client, FAISS_GCS_BUCKET, faiss_file, f"sample_data/{args.index_name}.faiss"
            )

            gcs_meta_path = upload_to_gcs(
                storage_client, FAISS_GCS_BUCKET, meta_file, f"sample_data/{args.index_name}_meta.pkl"
            )

        # Register in Firestore
        doc_id = register_in_firestore(
            args.index_name, gcs_faiss_path, gcs_meta_path, args.vector_count, args.dimension
        )

        print("\nSample data generation completed successfully!")
        print(f"FAISS Index: {gcs_faiss_path}")
        print(f"Metadata: {gcs_meta_path}")
        print(f"Firestore Document ID: {doc_id}")
        print(f"Vector Count: {args.vector_count}")
        print(f"Dimension: {args.dimension}")

    except Exception as e:
        logger.error(f"Failed to generate sample data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
