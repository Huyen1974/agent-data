import argparse
import logging
import faiss
from agent_data.vector_store.qdrant_store import QdrantStore
from qdrant_client.http.models import PointStruct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_faiss_to_qdrant(faiss_index_path: str, collection_name: str, batch_size: int = 100):
    """
    Migrate vectors from FAISS index to Qdrant collection.

    Args:
        faiss_index_path: Path to FAISS index file
        collection_name: Target Qdrant collection name
        batch_size: Number of vectors to process per batch

    Returns:
        Dict with migration status and results
    """
    try:
        # Load FAISS index
        index = faiss.read_index(faiss_index_path)
        dimension = index.d
        num_vectors = index.ntotal

        logger.info(f"Loaded FAISS index with {num_vectors} vectors of dimension {dimension}")

        if num_vectors == 0:
            logger.warning("FAISS index is empty, nothing to migrate")
            return {"status": "success", "migrated_count": 0}

        # Initialize QdrantStore
        qdrant_store = QdrantStore()

        # Process vectors in batches
        migrated_count = 0

        for i in range(0, num_vectors, batch_size):
            batch_end = min(i + batch_size, num_vectors)
            batch_size_actual = batch_end - i

            # Extract vectors for this batch
            batch_points = []

            for j in range(batch_size_actual):
                vector_idx = i + j

                # Handle different FAISS index types
                if isinstance(index, faiss.IndexIDMap):
                    # For IndexIDMap, get vector from underlying index
                    vector = index.index.reconstruct(vector_idx)
                else:
                    # For regular indices
                    vector = index.reconstruct(vector_idx)

                # Create point with auto-generated ID and basic payload
                point_id = vector_idx + 1  # Start IDs from 1
                payload = {"source": "FAISS_migration", "original_index": vector_idx, "tag": "migrated"}

                batch_points.append(PointStruct(id=point_id, vector=vector.tolist(), payload=payload))

            # Upsert batch to Qdrant
            qdrant_store.client.upsert(collection_name=collection_name, points=batch_points)

            migrated_count += len(batch_points)
            logger.info(f"Migrated batch {i} to {batch_end} of {num_vectors} ({migrated_count} total)")

        logger.info(f"Successfully migrated {migrated_count} vectors to Qdrant collection '{collection_name}'")
        return {"status": "success", "migrated_count": migrated_count}

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        return {"status": "failed", "error": str(e), "migrated_count": 0}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate FAISS index to Qdrant collection.")
    parser.add_argument("--faiss-index", required=True, help="Path to FAISS index file")
    parser.add_argument("--collection-name", required=True, help="Qdrant collection name")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for migration")

    args = parser.parse_args()

    result = migrate_faiss_to_qdrant(args.faiss_index, args.collection_name, args.batch_size)
    print(result)
