import sys
import logging

# Set up logger early
logger = logging.getLogger(__name__)
logger.info(f"sys.path in Cloud Run at top of register_tools.py: {sys.path}")

# Initialize API key masking middleware for security
try:
    from .api_key_middleware import setup_global_api_key_masking

    setup_global_api_key_masking()
    logger.info("API key masking middleware initialized successfully")
except ImportError as e:
    logger.warning(f"Failed to initialize API key masking middleware: {e}")

# --- Core Tool Imports (No external dependencies like Faiss/OpenAI) ---
from .save_text_tool import save_text
from .add_numbers_tool import add_numbers
from .multiply_numbers_tool import multiply_numbers
from .echo_tool import echo
from .get_registered_tools_tool import get_registered_tools
from .delay_tool import delay_tool

# --- Metadata/Document Management Tool Imports (May use local file system/pickle) ---
from .save_document_tool import save_document
from .vectorize_document_tool import vectorize_document
from .update_metadata_tool import update_metadata
from .query_metadata_tool import query_metadata
from .multi_update_metadata_tool import multi_update_metadata
from .bulk_delete_metadata_tool import bulk_delete_metadata
from .bulk_update_metadata_tool import bulk_update_metadata
from .multi_field_update_tool import multi_field_update
from .delete_by_tag_tool import delete_by_tag_sync
from .bulk_upload_tool import bulk_upload_sync
from .search_by_payload_tool import search_by_payload_sync

# --- Metadata Search/Query Tool Imports (Local implementations) ---
from .semantic_search_local_tool import semantic_search_local
from .find_metadata_by_key_tool import find_metadata_by_key
from .semantic_search_metadata_tool import semantic_search_metadata
from .semantic_search_by_author_tool import semantic_search_by_author
from .semantic_search_by_year_tool import semantic_search_by_year
from .semantic_search_by_keyword_tool import semantic_search_by_keyword
from .conditional_search_metadata_tool import conditional_search_metadata
from .semantic_search_multiple_fields_tool import semantic_search_multiple_fields
from .sort_metadata_tool import sort_metadata
from .advanced_semantic_search_tool import advanced_semantic_search

# --- Metadata Tree Tool Imports (Local graph/tree logic) ---
from .create_metadata_tree_tool import create_metadata_tree
from .view_metadata_tree_tool import view_metadata_tree
from .delete_metadata_node_tool import delete_metadata_node
from .update_metadata_node_tool import update_metadata_node
from .depth_first_search_tool import depth_first_search
from .rebuild_metadata_tree_tool import rebuild_metadata_tree
from .semantic_search_metadata_tree_tool import semantic_search_metadata_tree
from .validate_metadata_tree_tool import validate_metadata_tree

# --- Embedding Generation/Search Tool Imports (Local/Simple) ---
from .generate_embedding_tool import generate_embedding
from .semantic_similarity_search_tool import semantic_similarity_search
from .batch_generate_embeddings_tool import batch_generate_embeddings

# --- Advanced/Analysis Tool Imports (Local implementations) ---
from .semantic_expand_metadata_tool import semantic_expand_metadata
from .semantic_filter_metadata_tool import semantic_filter_metadata
from .analyze_metadata_trends_tool import analyze_metadata_trends
from .aggregate_metadata_tool import aggregate_metadata
from .detect_anomalies_tool import detect_anomalies
from .metadata_statistics_tool import metadata_statistics

# --- Error Tool Import ---
from .error_tool import raise_error_tool

# --- Qdrant Vector Store Tool Imports ---
try:
    from .qdrant_vector_tools import (
        qdrant_upsert_vector,
        qdrant_query_by_tag,
        qdrant_delete_by_tag,
        qdrant_get_count,
        qdrant_health_check,
        save_vector_to_qdrant,
        search_vectors_qdrant,
    )
    from .qdrant_embedding_tools import (
        qdrant_generate_and_store_embedding,
        qdrant_semantic_search,
        qdrant_batch_generate_embeddings,
        semantic_search_qdrant,
    )

    # Import synchronous wrappers for MCP integration
    from .qdrant_sync_wrappers import (
        qdrant_health_check_sync,
        qdrant_get_count_sync,
        qdrant_upsert_vector_sync,
        qdrant_query_by_tag_sync,
        qdrant_delete_by_tag_sync,
        qdrant_semantic_search_sync,
        qdrant_generate_and_store_embedding_sync,
        semantic_search_qdrant_sync,
    )

    QDRANT_TOOLS_AVAILABLE = True
except ImportError:
    # Use logger after it's defined in get_all_tool_functions if needed
    QDRANT_TOOLS_AVAILABLE = False

# --- External Dependency Tool Registration ---
# Import the flags and the tool functions directly using relative paths for consistency
from .external_tool_registry import (
    FAISS_AVAILABLE,
    OPENAI_AVAILABLE,
    generate_embedding_real,
    semantic_search_cosine,
    clear_embeddings,
)

# --- Conditionally import FAISS-dependent tools ---
# Define placeholders
_faiss_save = None
_faiss_load = None
_faiss_query_advanced = None
_faiss_rebuild_tree = None

# Import the query tool using relative path
from .query_metadata_faiss_tool import query_metadata_faiss

if FAISS_AVAILABLE:
    try:
        # Use relative paths for conditional imports
        from .save_metadata_to_faiss_tool import save_metadata_to_faiss as _faiss_save
        from .load_metadata_from_faiss_tool import load_metadata_from_faiss as _faiss_load
        from .advanced_query_faiss_tool import advanced_query_faiss as _faiss_query_advanced
        from .rebuild_metadata_tree_from_faiss_tool import rebuild_metadata_tree_from_faiss as _faiss_rebuild_tree
    except ImportError as ie:
        faiss_logger_init = logging.getLogger(__name__)
        faiss_logger_init.warning(f"FAISS is AVAILABLE but absolute import failed: {ie}. FAISS tools may not work.")
# --- End Conditional FAISS Import ---


# --- Registration function for AgentDataAgent ---
def register_tools(agent):
    """Registers all available tools with the agent instance's ToolsManager."""
    logger.info(f"Registering tools for agent: {agent.name}")
    all_tools_dict = get_all_tool_functions()
    for name, func in all_tools_dict.items():
        try:
            pass_context = False
            # Tools that require agent_context should be listed here
            if name in ["query_metadata_faiss", "generate_embedding_real", "get_registered_tools"]:
                pass_context = True
                logger.info(f"Registering tool '{name}' with pass_agent_context=True")

            agent.tools_manager.register_tool(name=name, tool_function=func, pass_agent_context=pass_context)
            # logger.debug(f"Successfully registered tool: {name}") # Too verbose for INFO
        except Exception as e:
            logger.error(f"Failed to register tool '{name}': {e}", exc_info=True)
    registered_count = len(agent.tools_manager.tools)
    logger.info(f"Completed tool registration for {agent.name}. Total tools registered: {registered_count}")


# --- Tool Function Lister ---
def get_all_tool_functions() -> dict:
    """Returns a dictionary of all potentially registerable tool functions.
    Useful if manual registration or discovery is needed.
    This function assumes tools are imported into this module's namespace.
    """

    # Log the status of dependency flags
    logger.info(
        f"Checking dependencies inside get_all_tool_functions: FAISS_AVAILABLE={FAISS_AVAILABLE}, OPENAI_AVAILABLE={OPENAI_AVAILABLE}"
    )

    # Manually list core/local tools
    local_tools = {
        "save_text": save_text,
        "add_numbers": add_numbers,
        "multiply_numbers": multiply_numbers,
        "echo": echo,
        "get_registered_tools": get_registered_tools,
        "delay": delay_tool,
        "save_document": save_document,
        "vectorize_document": vectorize_document,
        "update_metadata": update_metadata,
        "query_metadata": query_metadata,
        "multi_update_metadata": multi_update_metadata,
        "bulk_delete_metadata": bulk_delete_metadata,
        "bulk_update_metadata": bulk_update_metadata,
        "multi_field_update": multi_field_update,
        "delete_by_tag": delete_by_tag_sync,
        "bulk_upload": bulk_upload_sync,
        "search_by_payload": search_by_payload_sync,
        "semantic_search_local": semantic_search_local,
        "find_metadata_by_key": find_metadata_by_key,
        "semantic_search_metadata": semantic_search_metadata,
        "semantic_search_by_author": semantic_search_by_author,
        "semantic_search_by_year": semantic_search_by_year,
        "semantic_search_by_keyword": semantic_search_by_keyword,
        "conditional_search_metadata": conditional_search_metadata,
        "semantic_search_multiple_fields": semantic_search_multiple_fields,
        "sort_metadata": sort_metadata,
        "advanced_semantic_search": advanced_semantic_search,
        "create_metadata_tree": create_metadata_tree,
        "view_metadata_tree": view_metadata_tree,
        "delete_metadata_node": delete_metadata_node,
        "update_metadata_node": update_metadata_node,
        "depth_first_search": depth_first_search,
        "rebuild_metadata_tree": rebuild_metadata_tree,
        "semantic_search_metadata_tree": semantic_search_metadata_tree,
        "validate_metadata_tree": validate_metadata_tree,
        "generate_embedding": generate_embedding,
        "semantic_similarity_search": semantic_similarity_search,
        "batch_generate_embeddings": batch_generate_embeddings,
        "semantic_expand_metadata": semantic_expand_metadata,
        "semantic_filter_metadata": semantic_filter_metadata,
        "analyze_metadata_trends": analyze_metadata_trends,
        "aggregate_metadata": aggregate_metadata,
        "detect_anomalies": detect_anomalies,
        "metadata_statistics": metadata_statistics,
        "error_tool": raise_error_tool,
    }

    logger.info(f"Base local tools collected: {list(local_tools.keys())}")

    # Add FAISS tools if available
    if FAISS_AVAILABLE:
        logger.info("FAISS_AVAILABLE is True, attempting to add FAISS tools...")
        if _faiss_save:
            local_tools["save_metadata_to_faiss"] = _faiss_save
        if _faiss_load:
            local_tools["load_metadata_from_faiss"] = _faiss_load
        # Register the query tool with the correct name
        local_tools["query_metadata_faiss"] = query_metadata_faiss
        if _faiss_query_advanced:
            local_tools["advanced_query_faiss"] = _faiss_query_advanced
        if _faiss_rebuild_tree:
            local_tools["rebuild_metadata_tree_from_faiss"] = _faiss_rebuild_tree
        logger.info(f"FAISS tools added. Current tools: {list(local_tools.keys())}")
    else:
        logger.warning("FAISS_AVAILABLE is False. Skipping FAISS tools.")

    # Add external tools (if available)
    external_tools = {}
    if OPENAI_AVAILABLE:
        logger.info("OPENAI_AVAILABLE is True, attempting to add OpenAI tools...")
        external_tools["generate_embedding_real"] = generate_embedding_real
        external_tools["semantic_search_cosine"] = semantic_search_cosine
        external_tools["clear_embeddings"] = clear_embeddings
        logger.info(f"OpenAI tools added: {list(external_tools.keys())}")
    else:
        logger.warning("OPENAI_AVAILABLE is False. Skipping OpenAI tools.")

    local_tools.update(external_tools)

    # Add Qdrant tools if available
    if QDRANT_TOOLS_AVAILABLE:
        logger.info("QDRANT_TOOLS_AVAILABLE is True, attempting to add Qdrant tools...")
        qdrant_tools = {
            # Async tools (for agent use)
            "qdrant_upsert_vector": qdrant_upsert_vector,
            "qdrant_query_by_tag": qdrant_query_by_tag,
            "qdrant_delete_by_tag": qdrant_delete_by_tag,
            "qdrant_get_count": qdrant_get_count,
            "qdrant_health_check": qdrant_health_check,
            "save_vector_to_qdrant": save_vector_to_qdrant,
            "search_vectors_qdrant": search_vectors_qdrant,
            "qdrant_generate_and_store_embedding": qdrant_generate_and_store_embedding,
            "qdrant_semantic_search": qdrant_semantic_search,
            "qdrant_batch_generate_embeddings": qdrant_batch_generate_embeddings,
            "semantic_search_qdrant": semantic_search_qdrant,
            # Synchronous wrappers (for MCP use)
            "qdrant_health_check_sync": qdrant_health_check_sync,
            "qdrant_get_count_sync": qdrant_get_count_sync,
            "qdrant_upsert_vector_sync": qdrant_upsert_vector_sync,
            "qdrant_query_by_tag_sync": qdrant_query_by_tag_sync,
            "qdrant_delete_by_tag_sync": qdrant_delete_by_tag_sync,
            "qdrant_semantic_search_sync": qdrant_semantic_search_sync,
            "qdrant_generate_and_store_embedding_sync": qdrant_generate_and_store_embedding_sync,
            "semantic_search_qdrant_sync": semantic_search_qdrant_sync,
        }
        local_tools.update(qdrant_tools)
        logger.info(f"Qdrant tools added: {list(qdrant_tools.keys())}")
    else:
        logger.warning("QDRANT_TOOLS_AVAILABLE is False. Skipping Qdrant tools.")

    # import logging # No longer needed here
    # logger = logging.getLogger(__name__) # Already defined
    logger.debug(f"get_all_tool_functions returning: {list(local_tools.keys())}")
    return local_tools


# Example: Decorate tools directly if possible (would require editing tool files)
# import mcp
# @mcp.tool()
# def echo(text: str) -> str:
#     return text

# Or, adapt register_tools to use mcp.register:
# def register_mcp_tools(mcp_instance):
#     all_tools = get_all_tool_functions()
#     for name, func in all_tools.items():
#         try:
#             mcp_instance.register(func, name=name)
#         except Exception as e:
#             logger = logging.getLogger(__name__)
#             logger.error(f"Failed to register tool '{name}' with MCP: {e}")
