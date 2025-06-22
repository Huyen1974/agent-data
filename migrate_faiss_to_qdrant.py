from typing import Dict, List, Any
import faiss
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct


def migrate_faiss_to_qdrant(
    faiss_index_path: str,
    qdrant_client: QdrantClient,
    collection_name: str,
    payloads: List[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    stats = {"vectors_processed": 0, "errors": 0, "skipped": 0}
    index = faiss.read_index(faiss_index_path)

    if isinstance(index, faiss.IndexIDMap):
        # For IndexIDMap, reconstruct_n might operate on the underlying index's sequential IDs
        # The vectors are stored in the .index attribute (the base_index)
        if index.ntotal > 0:
            vectors = index.index.reconstruct_n(0, index.ntotal)
        else:
            vectors = np.array([])  # Handle empty index
    else:
        vectors = index.reconstruct_n(0, index.ntotal)

    payloads = payloads or [{}] * index.ntotal

    if len(payloads) != index.ntotal:
        stats["errors"] += 1
        # It is better to provide a more descriptive error message
        stats["error_message"] = "Payloads length does not match the number of vectors in the FAISS index."
        return stats

    points = [
        PointStruct(id=payloads[i]["id"], vector=vectors[i].tolist(), payload=payloads[i]) for i in range(index.ntotal)
    ]
    stats["vectors_processed"] = len(points)

    if not dry_run:
        try:
            qdrant_client.upsert(collection_name=collection_name, points=points)
        except Exception as e:
            stats["errors"] += 1
            stats["error_message"] = str(e)

    return stats
