import pickle
import os
import time
from typing import Dict, Any
import logging

# Removed direct OpenAI client import/setup and get_secret - handled by external registry
# Removed direct retry import - handled by external registry
# Removed direct secret manager import - handled by external registry

logger = logging.getLogger(__name__)

# Constants remain for local use if needed, registry defines primary ones
FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY_IO = 1

# The actual tool function - expects get_openai_embedding to be available if called
# It will be called *by* the external registry, which handles client setup.
from .external_tool_registry import get_openai_embedding, openai_client, FAISS_AVAILABLE


def generate_embedding_real(index_name: str, key: str, text_field: str = "content") -> Dict[str, Any]:
    """
    Generates a real embedding using OpenAI API for a specific metadata node
    (based on its 'text_field' or 'content') and updates the metadata file.
    (Core logic only - assumes client and FAISS availability checked by registry)
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not openai_client:
        return {"status": "failed", "error": "OpenAI client not available."}
    if not FAISS_AVAILABLE:
        return {"status": "failed", "error": "FAISS library not available."}
    if not os.path.exists(meta_path):
        return {"status": "failed", "error": f"Metadata file not found for '{index_name}'."}

    try:
        with open(meta_path, "rb") as f:
            loaded_data = pickle.load(f)
    except Exception as e:
        return {"status": "failed", "error": f"Failed to load metadata file '{meta_path}': {e}"}

    if not isinstance(loaded_data, dict) or "metadata" not in loaded_data or "key_to_id" not in loaded_data:
        return {"status": "failed", "error": f"Invalid metadata format in '{meta_path}'."}

    metadata_dict = loaded_data["metadata"]
    if key not in metadata_dict or not isinstance(metadata_dict[key], dict):
        return {"status": "failed", "error": f"Key '{key}' not found or invalid metadata format."}

    node_metadata = metadata_dict[key]

    # Find text to embed
    text_to_embed = None
    fields_to_check = [text_field, "content", "description", "summary", "text"]
    for field in fields_to_check:
        if field in node_metadata and isinstance(node_metadata[field], str):
            text_to_embed = node_metadata[field]
            logger.debug(f"Using field '{field}' for embedding key '{key}'.")
            break

    if not text_to_embed:
        return {"status": "failed", "error": f"No suitable text field found for key '{key}' in {fields_to_check}."}

    # Generate Real Embedding (uses retry internally via get_openai_embedding)
    logger.info(f"Generating real embedding for key '{key}'...")
    try:
        real_embedding = get_openai_embedding(text_to_embed)
        if real_embedding is None:
            return {"status": "failed", "error": f"Failed to generate embedding for key '{key}' after retries."}
    except Exception as e:
        logger.error(f"Embedding generation failed for key '{key}': {e}")
        return {"status": "failed", "error": f"Embedding generation failed: {e}"}

    node_metadata["embedding"] = real_embedding
    loaded_data["metadata"][key] = node_metadata

    # Save Metadata with Retry
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)
            embedding_dim = len(real_embedding)
            logger.info(f"Successfully generated/saved real embedding (dim={embedding_dim}) for key '{key}'.")
            return {
                "status": "success",
                "key": key,
                "embedding_dim": embedding_dim,
                "embedding_preview": real_embedding[:3] + ["..."],
            }
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} to save metadata failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_IO)
            else:
                return {"status": "failed", "error": f"Failed to save metadata after {MAX_RETRIES} attempts: {e}"}

    return {"status": "failed", "error": "Save failed after multiple retries."}


# Removed example usage block
