import pickle
import os

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Any
import logging

# Import the necessary functions/variables from the external registry
from .external_tool_registry import get_openai_embedding, openai_client, FAISS_AVAILABLE, TOP_N_DEFAULT

logger = logging.getLogger(__name__)

# Constants
FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3  # Local I/O retries mainly
RETRY_DELAY = 1  # seconds


def semantic_search_cosine(
    index_name: str, query_text: str, threshold: float = 0.8, top_n: int = TOP_N_DEFAULT
) -> Dict[str, Any]:
    """
    Performs semantic similarity search using cosine similarity against a text query.
    (Core logic only - assumes client and FAISS availability checked by registry)
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not openai_client:
        return {"status": "failed", "error": "OpenAI client not available."}
    if not FAISS_AVAILABLE:
        return {"status": "failed", "error": "FAISS library not available."}
    if not os.path.exists(meta_path):
        return {"status": "failed", "error": f"Metadata file not found for '{index_name}'."}

    # Generate query embedding (uses retry via get_openai_embedding)
    try:
        query_embedding_list = get_openai_embedding(query_text)
        if query_embedding_list is None:
            return {"status": "failed", "error": f"Could not generate query embedding after retries."}
        query_embedding = np.array(query_embedding_list).reshape(1, -1)
        query_dim = query_embedding.shape[1]
    except Exception as e:
        logger.error(f"Failed to get/process query embedding: {e}")
        return {"status": "failed", "error": f"Query embedding error: {e}"}

    # Load metadata (simple load)
    try:
        with open(meta_path, "rb") as f:
            loaded_data = pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load metadata '{meta_path}': {e}")
        return {"status": "failed", "error": f"Metadata load error: {e}"}

    if not isinstance(loaded_data, dict) or "metadata" not in loaded_data:
        return {"status": "failed", "error": f"Invalid metadata format in '{meta_path}'."}

    metadata_dict = loaded_data["metadata"]

    # Compare embeddings
    embeddings_to_compare = []
    keys_to_compare = []
    for key, item_metadata in metadata_dict.items():
        if isinstance(item_metadata, dict) and "embedding" in item_metadata:
            try:
                emb_data = item_metadata["embedding"]
                if isinstance(emb_data, (list, np.ndarray)) and len(emb_data) > 0:
                    emb = np.array(emb_data)
                    if emb.ndim == 1 and emb.shape[0] == query_dim:
                        embeddings_to_compare.append(emb)
                        keys_to_compare.append(key)
                    else:
                        logger.warning(
                            f"Key '{key}' embedding dimension mismatch ({emb.shape} vs {query_dim}). Skipping."
                        )
            except Exception as e:
                logger.warning(f"Error processing embedding for key '{key}': {e}. Skipping.")

    if not keys_to_compare:
        logger.info(f"No valid embeddings found for comparison in '{index_name}'.")
        return {"status": "success", "query": query_text, "similar_items": []}

    # Calculate similarity
    try:
        embeddings_array = np.array(embeddings_to_compare)
        if embeddings_array.ndim == 1:
            embeddings_array = embeddings_array.reshape(1, -1)
        if embeddings_array.shape[1] != query_dim:
            return {"status": "failed", "error": "Internal dimension mismatch error before similarity calc."}
        similarity_scores = cosine_similarity(query_embedding, embeddings_array)[0]
    except Exception as e:
        logger.error(f"Cosine similarity calculation error: {e}")
        return {"status": "failed", "error": f"Similarity calculation error: {e}"}

    # Filter and sort results
    similar_items = [
        {"key": keys_to_compare[i], "cosine_similarity": round(float(score), 6)}
        for i, score in enumerate(similarity_scores)
        if score >= threshold
    ]
    sorted_similar = sorted(similar_items, key=lambda x: x["cosine_similarity"], reverse=True)
    top_similar = sorted_similar[:top_n]

    logger.info(f"Found {len(top_similar)} similar items (cosine >= {threshold}) for query '{query_text}'.")
    return {"status": "success", "query": query_text, "similar_items": top_similar}


# Removed example usage block
