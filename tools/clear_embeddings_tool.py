import logging
import os
import pickle
import time
from typing import Any

# Import FAISS_AVAILABLE check from registry
from .external_tool_registry import FAISS_AVAILABLE

logger = logging.getLogger(__name__)

FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY_IO = 1  # seconds


def clear_embeddings(index_name: str) -> dict[str, Any]:
    """
    Removes the 'embedding' field from all nodes in the specified index's metadata.
    (Core logic only - assumes FAISS availability checked by registry)
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    # Conceptually linked to FAISS, check availability
    if not FAISS_AVAILABLE:
        return {
            "status": "failed",
            "error": "FAISS library conceptually needed but not available.",
        }

    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for '{index_name}'.",
        }

    loaded_data = None
    # Load with Retry
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break
        except FileNotFoundError:
            return {
                "status": "failed",
                "error": "Metadata file disappeared during clear.",
            }
        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1} failed to load metadata '{meta_path}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_IO)
            else:
                return {
                    "status": "failed",
                    "error": f"Failed to load metadata after {MAX_RETRIES} attempts: {e}",
                }

    if not isinstance(loaded_data, dict) or "metadata" not in loaded_data:
        return {
            "status": "failed",
            "error": f"Invalid metadata format in '{meta_path}'.",
        }

    metadata_dict = loaded_data["metadata"]
    cleared_count = 0
    needs_saving = False

    # Remove Embeddings
    for key, item_metadata in metadata_dict.items():
        if isinstance(item_metadata, dict) and "embedding" in item_metadata:
            del item_metadata["embedding"]
            # No need to update metadata_dict[key] = item_metadata, deletion modifies the original dict item
            cleared_count += 1
            needs_saving = True

    if not needs_saving:
        logger.info(f"No embeddings found to clear in '{index_name}'.")
        return {
            "status": "success",
            "cleared_count": 0,
            "message": "No embeddings found.",
        }

    # Save with Retry
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)
            logger.info(
                f"Successfully cleared embeddings from {cleared_count} nodes in '{index_name}'."
            )
            return {"status": "success", "cleared_count": cleared_count}
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed to save metadata: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_IO)
            else:
                return {
                    "status": "failed",
                    "error": f"Failed to save metadata after {MAX_RETRIES} attempts: {e}",
                }

    return {"status": "failed", "error": "Save failed after multiple retries."}
