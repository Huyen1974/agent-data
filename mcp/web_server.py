import logging
import os
import json
import time
import sys
from flask import Flask, request, jsonify

# Removed storage import as it seems unused
# from google.cloud import storage

# Lazy import flag - tools will be loaded on first request
_tools_loaded = False
_all_tools = {}
_tool_loading_error = None

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -->> OPTIMIZED STARTUP LOGGING <<--
logger.info(f"--- Web Server Starting (OPTIMIZED) ---")
logger.info(f"Python Version: {sys.version}")
logger.info(f"Flask App Name: {app.name}")
# Defer dependency checking until first request
logger.info("Tool loading deferred until first request for faster startup")
# -->> END STARTUP LOGGING <<--


def _lazy_load_tools():
    """Lazy load tools on first request to reduce startup time."""
    global _tools_loaded, _all_tools, _tool_loading_error
    
    if _tools_loaded:
        return _all_tools, _tool_loading_error
    
    logger.info("Loading tools on first request...")
    start_time = time.time()
    
    try:
        # Import tool registration and dependency flags
        try:
            from ADK.agent_data.tools.register_tools import get_all_tool_functions
            from ADK.agent_data.tools.external_tool_registry import FAISS_AVAILABLE, OPENAI_AVAILABLE
            registry_imported = True
        except ImportError as e1:
            logger.warning(f"Initial import failed ({e1}), attempting relative path adjustment...")
            registry_imported = False
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                logger.info(f"Added {project_root} to sys.path")
                from ADK.agent_data.tools.register_tools import get_all_tool_functions
                from ADK.agent_data.tools.external_tool_registry import FAISS_AVAILABLE, OPENAI_AVAILABLE
                registry_imported = True
                logger.info("Successfully imported registry after path adjustment.")
            except ImportError as e2:
                logger.error(f"CRITICAL: Failed to import registry even after path adjustment: {e2}")
                get_all_tool_functions = lambda: {}
                FAISS_AVAILABLE = False
                OPENAI_AVAILABLE = False
                logger.error("CRITICAL: Using dummy get_all_tool_functions and flags!")
                registry_imported = False

        if registry_imported:
            logger.info(f"Dependency Check: FAISS_AVAILABLE={FAISS_AVAILABLE}, OPENAI_AVAILABLE={OPENAI_AVAILABLE}")
            _all_tools = get_all_tool_functions()
            logger.info(f"Successfully loaded {len(_all_tools)} tools: {list(_all_tools.keys())}")
        else:
            _all_tools = {}
            _tool_loading_error = "Failed to import registry module"
            
    except Exception as e:
        logger.error(f"Failed to load tools: {e}", exc_info=True)
        _all_tools = {}
        _tool_loading_error = str(e)
    
    _tools_loaded = True
    load_time = time.time() - start_time
    logger.info(f"Tool loading completed in {load_time:.3f}s")
    
    return _all_tools, _tool_loading_error


@app.route("/health", methods=["GET"])
def health_check():
    """Quick health check without loading tools."""
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200


@app.route("/execute", methods=["POST"])
def execute_tool():
    """Executes a tool based on MCP JSON format."""
    start_time = time.time()
    data = request.get_json()
    request_id = data.get("id", f"req-{int(start_time)}")  # Generate ID if missing

    if not data:
        logger.error(f"Request {request_id}: Received empty or invalid JSON data.")
        return (
            jsonify({"error": "Invalid or empty JSON request", "meta": {"status": "error", "request_id": request_id}}),
            400,
        )

    tool_name = data.get("tool_name")
    args = data.get("args", [])  # Default to empty list if 'args' is missing

    if not tool_name:
        logger.error(f"Request {request_id}: Missing 'tool_name' key in request payload.")
        return (
            jsonify(
                {
                    "error": "Missing 'tool_name' in request payload",
                    "meta": {"status": "error", "request_id": request_id},
                }
            ),
            400,
        )

    if not isinstance(args, list):
        logger.error(f"Request {request_id}: 'args' must be a list, got {type(args)}.")
        return jsonify({"error": "'args' must be a list", "meta": {"status": "error", "request_id": request_id}}), 400

    # --- Get tools lazily ---
    all_tools, loading_error = _lazy_load_tools()
    
    if loading_error:
        logger.error(f"Request {request_id}: Tool loading failed: {loading_error}")
        return (
            jsonify({
                "error": f"Tool system unavailable: {loading_error}",
                "meta": {"status": "error", "request_id": request_id}
            }),
            500,
        )

    tool_function = all_tools.get(tool_name)

    if not tool_function:
        available_tools_msg = list(all_tools.keys()) if all_tools else "No tools available"
        logger.error(f"Request {request_id}: Unknown tool: {tool_name}. Available: {available_tools_msg}")
        return (
            jsonify(
                {
                    "error": f"Unknown tool: {tool_name}. Available: {available_tools_msg}",
                    "meta": {"status": "error", "request_id": request_id},
                }
            ),
            404,
        )

    try:
        logger.info(f"Request {request_id}: Executing tool: {tool_name} with args: {args}")
        result = tool_function(*args)  # Unpack args for the function call
        logger.info(f"Request {request_id}: Tool {tool_name} executed successfully.")
        # Attempt to return JSON directly, handle potential serialization errors
        try:
            # Standard success response structure
            return jsonify(
                {
                    "result": result,
                    "meta": {
                        "status": "success",
                        "request_id": request_id,
                        "execution_time_ms": (time.time() - start_time) * 1000,
                    },
                }
            )
        except TypeError as e:
            logger.warning(
                f"Request {request_id}: Tool '{tool_name}' result type {type(result)} not directly JSON serializable: {e}. Returning as string."
            )
            # Fallback for non-serializable results
            return jsonify(
                {
                    "result": str(result),
                    "meta": {
                        "status": "success",
                        "request_id": request_id,
                        "execution_time_ms": (time.time() - start_time) * 1000,
                        "serialization_warning": "Result converted to string",
                    },
                }
            )

    except Exception as e:
        logger.error(
            f"Request {request_id}: Error executing tool {tool_name}: {str(e)}", exc_info=True
        )  # Log stack trace
        return (
            jsonify(
                {
                    "error": f"Error executing tool '{tool_name}': {str(e)}",
                    "meta": {
                        "status": "error",
                        "request_id": request_id,
                        "execution_time_ms": (time.time() - start_time) * 1000,
                    },
                }
            ),
            500,
        )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Use os.environ.get for Cloud Run compatibility
    logger.info(f"Starting Flask server on host 0.0.0.0 port {port}")
    # Use '0.0.0.0' to be accessible externally, required by Cloud Run
    # Turn off debug mode for production/Cloud Run
    app.run(host="0.0.0.0", port=port, debug=False)
