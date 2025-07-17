import asyncio
import logging
import os
import pickle
import sys
import time
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ADK.agent_data.agent.agent_data_agent import AgentDataAgent

# --- Setup Logger ---
# Moved logger initialization to the top
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)  # Add basic config if not configured elsewhere

# Attempt to import external dependencies, handle gracefully if not present
try:
    import openai
    from retry import retry as retry_decorator

    OPENAI_AVAILABLE = True
    logger.info("OpenAI import successful.")
    # Define the actual retry decorator only if openai is available
    openai_retry = retry_decorator(
        openai.APIError, tries=3, delay=2, backoff=2, logger=logging.getLogger(__name__)
    )
except ImportError as e:
    logger.error(f"OpenAI import failed: {e}", exc_info=True)
    print(f"ERROR: OpenAI import failed: {e}", file=sys.stderr)
    openai = None

    # Define dummy decorator if retry or openai is not installed
    def retry_decorator(*args, **kwargs):
        return lambda f: f

    def openai_retry(f):
        return f  # Dummy decorator that does nothing

    OPENAI_AVAILABLE = False
except Exception as e:
    logger.error(f"Unexpected error during OpenAI import: {e}", exc_info=True)
    print(f"ERROR: Unexpected OpenAI import error: {e}", file=sys.stderr)
    openai = None

    # Define dummy decorator if retry or openai is not installed
    def retry_decorator(*args, **kwargs):
        return lambda f: f

    def openai_retry(f):
        return f  # Dummy decorator that does nothing

    OPENAI_AVAILABLE = False

try:
    # Note: FAISS is often a system-level install, checking import might not be enough
    # We'll rely more on checks within the tools using it.
    import faiss

    FAISS_AVAILABLE = True  # Assume available if import succeeds
    logger.info("FAISS import successful.")
except ImportError as e:
    logger.error(f"FAISS import failed: {e}", exc_info=True)
    print(f"ERROR: FAISS import failed: {e}", file=sys.stderr)
    faiss = None
    FAISS_AVAILABLE = False
except Exception as e:
    logger.error(f"Unexpected error during FAISS import: {e}", exc_info=True)
    print(f"ERROR: Unexpected FAISS import error: {e}", file=sys.stderr)
    faiss = None
    FAISS_AVAILABLE = False


# --- Shared Constants ---
FAISS_DIR = "ADK/agent_data/faiss_indices"
MAX_RETRIES = 3
RETRY_DELAY_API = 2  # seconds for external API calls
RETRY_DELAY_IO = 1  # seconds for local I/O
EMBEDDING_MODEL = "text-embedding-3-small"  # Or another model
TOP_N_DEFAULT = 5  # Max number of similar items to return

# --- OpenAI Client Setup ---
openai_client = None
openai_async_client = None
openai_api_key = os.environ.get(
    "OPENAI_API_KEY"
)  # Prefer env var for simplicity in MCP

if OPENAI_AVAILABLE and openai_api_key:
    try:
        openai_client = openai.OpenAI(api_key=openai_api_key)
        openai_async_client = openai.AsyncOpenAI(api_key=openai_api_key)
        logger.info("OpenAI client initialized successfully via external registry.")
    except openai.OpenAIError as e:
        logger.error(f"Error initializing OpenAI client in external registry: {e}")
        openai_client = None  # Ensure client is None if init fails
        openai_async_client = None
else:
    if not OPENAI_AVAILABLE:
        logger.warning(
            "OpenAI library not found. Tools requiring OpenAI embeddings will not be available."
        )
    elif not openai_api_key:
        logger.warning(
            "OPENAI_API_KEY environment variable not set. Tools requiring OpenAI embeddings will not be available."
        )


# --- Tool Implementations (Moved from individual files) ---


# --- generate_embedding_real_tool ---
@openai_retry
async def get_openai_embedding(
    agent_context: AgentDataAgent,
    text_to_embed: str | list[str],
    model_name: str = EMBEDDING_MODEL,
    encoding_format: str = "float",
) -> dict[str, Any]:
    """Gets embedding for a text or list of texts using OpenAI API with retries."""
    print(
        "<<<< DEBUG: GET_OPENAI_EMBEDDING ENTERED (external_tool_registry.py) >>>>"
    )  # DEBUG ADDED
    # print(f"INSIDE get_openai_embedding, type of agent_context: {type(agent_context)}")
    if not openai_async_client:
        logger.warning("OpenAI async client not initialized. Cannot get embedding.")
        # Consistent error return for awaitable function
        return {"error": "OpenAI async client not initialized", "status_code": 500}
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI library not available inside get_openai_embedding.")
        return {"error": "OpenAI library not available", "status_code": 500}

    # Ensure input is a list of strings
    input_texts = text_to_embed if isinstance(text_to_embed, list) else [text_to_embed]
    # API recommendation: replace newlines
    processed_texts = [text.replace("\\n", " ") for text in input_texts]

    try:
        # logger.debug(f"Requesting OpenAI embedding for: {processed_texts} with model: {model_name}, format: {encoding_format}")
        print(
            "<<<< DEBUG: GET_OPENAI_EMBEDDING BEFORE openai_async_client.embeddings.create >>>>"
        )  # DEBUG ADDED
        response = await openai_async_client.embeddings.create(
            input=processed_texts, model=model_name, encoding_format=encoding_format
        )
        print(
            "<<<< DEBUG: GET_OPENAI_EMBEDDING AFTER openai_async_client.embeddings.create >>>>"
        )  # DEBUG ADDED
        # logger.debug(f"OpenAI embedding response received. Usage: {response.usage}")
        # Assuming a single embedding or first if multiple texts were for a single conceptual embedding
        result_dict = {
            "embedding": response.data[0].embedding,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
            "model_used": response.model,
        }
        # print(f"DEBUG get_openai_embedding returning: {result_dict.keys()}") # DEBUG REMOVED
        return result_dict
    except (
        openai.APIError
    ) as e:  # Renamed from APIConnectionError, RateLimitError, APIStatusError for broader catch
        logger.error(f"OpenAI API request failed to connect: {e}")
        # Consider if retry decorator handles this, or if specific return is needed.
        # For now, let retry handle it by re-raising, or return error if retry is exhausted.
        # If retry_decorator is a no-op (OPENAI_AVAILABLE=False), this will just propagate.
        # However, OPENAI_AVAILABLE check above should prevent this path if false.
        return {
            "error": f"OpenAI APIConnectionError: {e}",
            "status_code": e.status_code if hasattr(e, "status_code") else 503,
        }
    except openai.RateLimitError as e:
        logger.error(f"OpenAI API request exceeded rate limit: {e}")
        return {
            "error": f"OpenAI RateLimitError: {e}",
            "status_code": e.status_code if hasattr(e, "status_code") else 429,
        }
    except openai.APIStatusError as e:
        logger.error(f"OpenAI API returned an API Error: {e.status_code} {e.response}")
        return {
            "error": f"OpenAI APIStatusError: {e.message}",
            "status_code": e.status_code,
        }
    except Exception as e:
        print(
            f"<<<< DEBUG: GET_OPENAI_EMBEDDING CAUGHT EXCEPTION: {type(e).__name__} - {str(e)} >>>>"
        )  # DEBUG ADDED
        logger.error(
            f"An unexpected error occurred during OpenAI API call: {e}", exc_info=True
        )
        return {
            "error": f"Unexpected error during OpenAI API call: {e}",
            "status_code": 500,
        }


def generate_embedding_real(
    index_name: str, key: str, text_field: str = "content"
) -> dict[str, Any]:
    """
    Generates a real embedding using OpenAI API for a specific metadata node
    (based on its 'text_field' or 'content') and updates the metadata file.

    Args:
        index_name: The name of the FAISS index whose metadata to update.
        key: The key of the metadata node.
        text_field: The preferred field containing the text to embed (defaults to 'content').

    Returns:
        Dictionary with status and embedding details or error.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not openai_client:
        return {
            "status": "failed",
            "error": "OpenAI client not initialized. Cannot generate real embedding.",
        }
    if not FAISS_AVAILABLE:
        return {
            "status": "failed",
            "error": "FAISS library not available. Cannot operate on FAISS indices.",
        }

    if not os.path.exists(
        meta_path
    ):  # No need to check index_path, only modifying meta
        return {
            "status": "failed",
            "error": f"Metadata file not found for '{index_name}'. Cannot generate embedding.",
        }

    loaded_data = None
    # Load existing data
    try:
        # Simple load, retry handled by caller if needed, but critical failure if meta is bad
        with open(meta_path, "rb") as f:
            loaded_data = pickle.load(f)
    except Exception as e:
        return {
            "status": "failed",
            "error": f"Failed to load metadata file '{meta_path}': {e}",
        }

    if (
        loaded_data is None
        or "metadata" not in loaded_data
        or "key_to_id" not in loaded_data
    ):
        # key_to_id is crucial for potentially updating a FAISS index later if needed
        return {
            "status": "failed",
            "error": f"Invalid metadata file format for '{index_name}'. Missing 'metadata' or 'key_to_id'.",
        }

    metadata_dict = loaded_data["metadata"]

    if key not in metadata_dict:
        return {
            "status": "failed",
            "error": f"Key '{key}' not found in index '{index_name}'.",
        }

    node_metadata = metadata_dict[key]
    if not isinstance(node_metadata, dict):
        return {
            "status": "failed",
            "error": f"Metadata for key '{key}' is not a dictionary.",
        }

    # --- Find text to embed ---
    text_to_embed = None
    if text_field in node_metadata and isinstance(node_metadata[text_field], str):
        text_to_embed = node_metadata[text_field]
        logger.debug(f"Using primary field '{text_field}' for embedding.")
    elif "content" in node_metadata and isinstance(node_metadata["content"], str):
        text_to_embed = node_metadata["content"]
        logger.debug(
            f"Primary field '{text_field}' not found/invalid, using fallback 'content' field."
        )
    else:
        # Check common fields before giving up
        potential_fields = ["description", "summary", "text"]
        for field in potential_fields:
            if field in node_metadata and isinstance(node_metadata[field], str):
                text_to_embed = node_metadata[field]
                logger.debug(
                    f"Primary/fallback fields not found, using field '{field}'."
                )
                break
        if not text_to_embed:
            return {
                "status": "failed",
                "error": f"Could not find a valid string in common fields (e.g., '{text_field}', 'content', 'description') for key '{key}'.",
            }

    # --- Generate Real Embedding ---
    logger.info(f"Attempting to generate real embedding for key '{key}'...")
    try:
        embedding_result_dict = asyncio.run(
            get_openai_embedding(agent_context=None, text_to_embed=text_to_embed)
        )
        if (
            "embedding" not in embedding_result_dict
            or not embedding_result_dict["embedding"]
        ):
            return {
                "status": "failed",
                "error": f"Failed to generate embedding for key '{key}'. Error: {embedding_result_dict.get('error')}",
            }
        real_embedding = embedding_result_dict["embedding"]

        if real_embedding is None:  # Should be caught by the check above now
            # Error already logged by get_openai_embedding on failure
            return {
                "status": "failed",
                "error": f"Failed to generate embedding for key '{key}' after retries.",
            }
    except Exception as e:
        # Catch any exception bubbling up from retry failures
        logger.error(f"Embedding generation failed for key '{key}': {e}")
        return {
            "status": "failed",
            "error": f"Embedding generation failed for key '{key}': {e}",
        }

    node_metadata["embedding"] = real_embedding
    loaded_data["metadata"][key] = node_metadata  # Update the structure to be saved

    # --- Save Metadata with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)

            embedding_dim = len(real_embedding)
            logger.info(
                f"Successfully generated and saved real embedding (dim={embedding_dim}) for key '{key}'."
            )
            return {
                "status": "success",
                "key": key,
                "embedding_dim": embedding_dim,
                "embedding_preview": real_embedding[:3] + ["..."],
            }

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1} failed to save metadata after generating real embedding for '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_IO)
            else:
                # Return error instead of raising, more tool-friendly
                return {
                    "status": "failed",
                    "error": f"Failed to save metadata for '{index_name}' after {MAX_RETRIES} attempts: {e}",
                }

    return {
        "status": "failed",
        "error": "Unknown error after generating real embedding and save attempts.",
    }


# --- semantic_search_cosine_tool ---
def semantic_search_cosine(
    index_name: str, query_text: str, threshold: float = 0.8, top_n: int = TOP_N_DEFAULT
) -> dict[str, Any]:
    """
    Performs semantic similarity search using cosine similarity against a text query.

    Args:
        index_name: The name of the FAISS index to search within.
        query_text: The text query to search for similar items.
        threshold: The minimum cosine similarity score to consider an item similar.
        top_n: The maximum number of similar items to return.

    Returns:
        A dictionary with status: success and a list of similar items (key and similarity score),
        or status: failed and an error message.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    if not openai_client:
        return {
            "status": "failed",
            "error": "OpenAI client not initialized. Cannot generate query embedding.",
        }
    if not FAISS_AVAILABLE:
        return {
            "status": "failed",
            "error": "FAISS library not available. Cannot operate on FAISS indices.",
        }

    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for index '{index_name}'. Cannot search.",
        }

    # --- Generate embedding for the query text ---
    try:
        query_embedding_result_dict = asyncio.run(
            get_openai_embedding(agent_context=None, text_to_embed=query_text)
        )
        if (
            "embedding" not in query_embedding_result_dict
            or not query_embedding_result_dict["embedding"]
        ):
            return {
                "status": "failed",
                "error": f"Could not generate embedding for query text: '{query_text}'. Error: {query_embedding_result_dict.get('error')}",
            }
        query_embedding_list = query_embedding_result_dict["embedding"]

        if query_embedding_list is None:  # Should be caught by the check above now
            return {
                "status": "failed",
                "error": f"Could not generate embedding for query text: '{query_text}' after retries.",
            }
        query_embedding = np.array(query_embedding_list).reshape(1, -1)
        query_dim = query_embedding.shape[1]
    except Exception as e:
        logger.error(f"Failed to get or process query embedding: {e}")
        return {
            "status": "failed",
            "error": f"Could not generate or process embedding for query: {e}",
        }

    loaded_data = None
    # --- Load metadata --- (Simple load, critical failure if meta is bad)
    try:
        with open(meta_path, "rb") as f:
            loaded_data = pickle.load(f)
    except FileNotFoundError:
        return {
            "status": "failed",
            "error": f"Metadata file disappeared for index '{index_name}' during search.",
        }
    except Exception as e:
        logger.error(f"Failed to load metadata for FAISS index '{index_name}': {e}")
        return {
            "status": "failed",
            "error": f"Failed to load metadata for '{index_name}': {e}",
        }

    if loaded_data is None or "metadata" not in loaded_data:
        return {
            "status": "failed",
            "error": f"Invalid metadata file format for '{index_name}'. Missing 'metadata'.",
        }

    metadata_dict = loaded_data["metadata"]

    # --- Compare query embedding with stored embeddings ---
    similar_items = []
    embeddings_to_compare = []
    keys_to_compare = []

    # Collect valid embeddings from all nodes
    for key, item_metadata in metadata_dict.items():
        if isinstance(item_metadata, dict) and "embedding" in item_metadata:
            try:
                emb_data = item_metadata["embedding"]
                # Check if it's a list or numpy array and has content
                if isinstance(emb_data, (list, np.ndarray)) and len(emb_data) > 0:
                    emb = np.array(emb_data)  # Ensure it's a numpy array
                    if emb.ndim == 1 and emb.shape[0] == query_dim:
                        embeddings_to_compare.append(emb)
                        keys_to_compare.append(key)
                    else:
                        logger.warning(
                            f"Embedding for key '{key}' has incorrect shape/dimensions ({emb.shape}). Expected ({query_dim},). Skipping."
                        )
                elif emb_data is None:
                    logger.debug(f"Embedding for key '{key}' is None. Skipping.")
                else:
                    logger.warning(
                        f"Embedding data for key '{key}' is not a valid list/array or is empty ({type(emb_data)}). Skipping."
                    )

            except Exception as e:
                logger.warning(
                    f"Error processing embedding for key '{key}': {e}. Skipping."
                )

    if not keys_to_compare:
        logger.info(
            f"No nodes with valid embeddings found to compare against query '{query_text}' in index '{index_name}'."
        )
        return {"status": "success", "query": query_text, "similar_items": []}

    # Calculate cosine similarities in batch
    try:
        # Ensure embeddings_to_compare is a 2D array
        embeddings_array = np.array(embeddings_to_compare)
        if embeddings_array.ndim == 1:  # Handle case with only one comparable embedding
            embeddings_array = embeddings_array.reshape(1, -1)

        if embeddings_array.shape[1] != query_dim:
            # This should ideally not happen due to the check above, but safety first
            logger.error(
                f"Dimension mismatch before similarity calculation: query ({query_dim}) vs stored ({embeddings_array.shape[1]})."
            )
            return {"status": "failed", "error": "Internal dimension mismatch error."}

        similarity_scores = cosine_similarity(query_embedding, embeddings_array)[
            0
        ]  # Get the first (only) row
    except ValueError as ve:
        # More specific error for dimension mismatch
        logger.error(f"ValueError during cosine similarity calculation: {ve}")
        return {
            "status": "failed",
            "error": f"Similarity calculation error (likely dimension mismatch): {ve}",
        }
    except Exception as e:
        logger.error(f"Error calculating cosine similarity: {e}")
        return {
            "status": "failed",
            "error": f"Error calculating cosine similarity: {e}",
        }

    # Filter by threshold and collect results
    for i, score in enumerate(similarity_scores):
        if score >= threshold:
            similar_items.append(
                {"key": keys_to_compare[i], "cosine_similarity": round(float(score), 6)}
            )

    # Sort by score descending and take top N
    sorted_similar = sorted(
        similar_items, key=lambda x: x["cosine_similarity"], reverse=True
    )
    top_similar = sorted_similar[:top_n]

    logger.info(
        f"Found {len(top_similar)} similar items (cosine >= {threshold}) for query '{query_text}'."
    )
    return {"status": "success", "query": query_text, "similar_items": top_similar}


# --- clear_embeddings_tool ---
def clear_embeddings(index_name: str) -> dict[str, Any]:
    """
    Removes the 'embedding' field from all nodes in the specified index's metadata.

    Args:
        index_name: The name of the FAISS index whose metadata to clear embeddings from.

    Returns:
        A dictionary with status and count of nodes where embedding was removed.
    """
    meta_path = os.path.join(FAISS_DIR, f"{index_name}.meta")

    # No external dependencies needed to just clear, but check file exists
    if not os.path.exists(meta_path):
        return {
            "status": "failed",
            "error": f"Metadata file not found for '{index_name}'. Cannot clear embeddings.",
        }

    loaded_data = None
    # --- Load with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "rb") as f:
                loaded_data = pickle.load(f)
            break  # Success
        except FileNotFoundError:
            return {
                "status": "failed",
                "error": f"Metadata file disappeared for index '{index_name}' during clear embeddings.",
            }
        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1} failed to load metadata for FAISS index '{index_name}' (clear): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_IO)
            else:
                return {
                    "status": "failed",
                    "error": f"Failed to load metadata for '{index_name}' after {MAX_RETRIES} attempts: {e}",
                }

    if loaded_data is None or "metadata" not in loaded_data:
        return {
            "status": "failed",
            "error": f"Invalid metadata file format for '{index_name}'. Missing 'metadata'.",
        }

    metadata_dict = loaded_data["metadata"]
    cleared_count = 0
    needs_saving = False

    # --- Remove Embeddings ---
    for key, item_metadata in metadata_dict.items():
        # Check if it's a dict and has the 'embedding' key
        if isinstance(item_metadata, dict) and "embedding" in item_metadata:
            del item_metadata["embedding"]
            metadata_dict[key] = item_metadata  # Update dict in place
            cleared_count += 1
            needs_saving = True

    if not needs_saving:
        logger.info(f"No embeddings found to clear in index '{index_name}'.")
        return {
            "status": "success",
            "cleared_count": 0,
            "message": "No embeddings found to clear.",
        }

    loaded_data["metadata"] = (
        metadata_dict  # Ensure the modified dict is part of the saved structure
    )

    # --- Save with Retry ---
    for attempt in range(MAX_RETRIES):
        try:
            with open(meta_path, "wb") as f:
                pickle.dump(loaded_data, f)

            logger.info(
                f"Successfully cleared embeddings from {cleared_count} nodes in index '{index_name}'."
            )
            return {"status": "success", "cleared_count": cleared_count}

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1} failed to save metadata after clearing embeddings for '{index_name}': {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_IO)
            else:
                return {
                    "status": "failed",
                    "error": f"Failed to save metadata after clearing embeddings for '{index_name}' after {MAX_RETRIES} attempts: {e}",
                }

    return {
        "status": "failed",
        "error": "Unknown error after clearing embeddings and save attempts.",
    }


# --- Registration Function ---
def register_external_tools(agent):
    """Registers tools that depend on external libraries or services if available."""
    tools_registered = []
    if openai_client and FAISS_AVAILABLE:
        agent.tools_manager.register_tool(
            "generate_embedding_real", generate_embedding_real
        )
        tools_registered.append("generate_embedding_real")

        agent.tools_manager.register_tool(
            "semantic_search_cosine", semantic_search_cosine
        )
        tools_registered.append("semantic_search_cosine")

    # clear_embeddings only needs FAISS_DIR and pickle, but conceptually linked
    # Check if FAISS_AVAILABLE just to group it logically, though it doesn't use faiss lib directly.
    if FAISS_AVAILABLE:  # Or just True if we decide it's always available conceptually
        agent.tools_manager.register_tool("clear_embeddings", clear_embeddings)
        tools_registered.append("clear_embeddings")

    if tools_registered:
        logger.info(f"Registered external tools: {', '.join(tools_registered)}")
    else:
        logger.warning(
            "No external tools were registered due to missing dependencies or configuration (OpenAI API Key, Faiss library)."
        )
