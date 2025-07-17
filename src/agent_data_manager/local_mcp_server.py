import asyncio
import json
import logging
import os
import sys

from agent_data_manager.agent.agent_data_agent import AgentDataAgent
from agent_data_manager.tools.register_tools import register_tools

# Import QdrantStore for vector operations
try:
    from agent_data_manager.vector_store.qdrant_store import QdrantStore
except ImportError:
    QdrantStore = None
    logging.warning("QdrantStore not found. Vector operations will be unavailable.")

# Import MockQdrantStore for testing
try:
    # Try multiple import paths for MockQdrantStore
    try:
        from tests.mocks.mock_qdrant_store import MockQdrantStore
    except ImportError:
        # Fallback: add path and import
        workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        mock_path = os.path.join(workspace_root, "tests", "mocks")
        if mock_path not in sys.path:
            sys.path.append(mock_path)
        from mock_qdrant_store import MockQdrantStore
except ImportError:
    MockQdrantStore = None
    logging.warning("MockQdrantStore not found. Mock operations will be unavailable.")

# Import QdrantVectorizationTool for Cursor integration
try:
    from agent_data_manager.tools.qdrant_vectorization_tool import (
        QdrantVectorizationTool,
    )
except ImportError:
    QdrantVectorizationTool = None
    logging.warning(
        "QdrantVectorizationTool not found. Cursor integration will be unavailable."
    )

# Configure logging - reduce level for subprocess stability
log_level = logging.ERROR if os.getenv("USE_MOCK_QDRANT") == "1" else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)  # Log to stderr

# Global asyncio loop and vectorization tool
main_loop = None
vectorization_tool = None


def main():
    global main_loop, vectorization_tool
    logging.info("Initializing AgentDataAgent...")
    agent = AgentDataAgent()
    register_tools(agent)

    # Create a single asyncio loop for the entire session
    main_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(main_loop)
    logging.info("Created main asyncio loop")

    # Initialize QdrantVectorizationTool for Cursor integration
    if QdrantVectorizationTool:
        try:
            vectorization_tool = QdrantVectorizationTool()
            logging.info("QdrantVectorizationTool initialized for Cursor integration.")
        except Exception as e:
            logging.error(f"Failed to initialize QdrantVectorizationTool: {e}")
            vectorization_tool = None

    # Initialize QdrantStore based on environment variable
    qdrant_store = None
    use_mock = os.getenv("USE_MOCK_QDRANT", "0") == "1"

    if use_mock and MockQdrantStore:
        try:
            qdrant_store = MockQdrantStore()
            logging.info("MockQdrantStore initialized successfully for testing.")
        except Exception as e:
            logging.error(f"Failed to initialize MockQdrantStore: {e}")
    elif QdrantStore:
        try:
            qdrant_store = QdrantStore()
            logging.info("QdrantStore initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize QdrantStore: {e}")

    registered_tools = list(agent.tools_manager.tools.keys())
    logging.info(f"Agent initialized. Registered tools: {registered_tools}")
    logging.info(f"Using mock QdrantStore: {use_mock}")
    logging.info("MCP Server started. Waiting for JSON input via stdin...")

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            logging.info(f"Received raw input: {line}")
            try:
                input_data = json.loads(line)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON: {e}")
                error_response = json.dumps({"error": f"Invalid JSON input: {e}"})
                print(error_response, flush=True)  # Output JSON error to stdout
                continue

            if not isinstance(input_data, dict):
                logging.error("Input data is not a JSON object (dictionary).")
                error_response = json.dumps({"error": "Input must be a JSON object."})
                print(error_response, flush=True)
                continue

            logging.info(f"Parsed input data: {input_data}")

            tool_name = input_data.get("tool_name")

            if not tool_name:
                logging.error("Missing 'tool_name' in input JSON.")
                error_response = json.dumps(
                    {"error": "Missing 'tool_name' in input JSON."}
                )
                print(error_response, flush=True)
                continue

            # Handle Cursor IDE document storage integration
            if vectorization_tool and tool_name in [
                "cursor_save_document",
                "save_document_to_qdrant",
            ]:
                try:
                    result = main_loop.run_until_complete(
                        handle_cursor_document_storage(
                            vectorization_tool, tool_name, input_data
                        )
                    )
                    result_json = json.dumps(
                        {
                            "result": result,
                            "meta": {"status": "success", "tool": "cursor_integration"},
                        }
                    )
                    print(result_json, flush=True)
                    logging.info(
                        f"Sent Cursor integration result to stdout: {result_json}"
                    )
                    continue
                except Exception as e:
                    logging.exception(f"Error during Cursor integration '{tool_name}':")
                    error_response = json.dumps(
                        {
                            "error": str(e),
                            "meta": {"status": "error", "tool": "cursor_integration"},
                        }
                    )
                    print(error_response, flush=True)
                    continue

            # Handle QdrantStore-specific tools
            if qdrant_store and tool_name in ["upsert_vector", "query_vectors_by_tag"]:
                try:
                    result = handle_qdrant_tool(qdrant_store, tool_name, input_data)
                    result_json = json.dumps(
                        {"result": result, "meta": {"status": "success"}}
                    )
                    print(result_json, flush=True)
                    logging.info(f"Sent QdrantStore result to stdout: {result_json}")
                    continue
                except Exception as e:
                    logging.exception(
                        f"Error during QdrantStore operation '{tool_name}':"
                    )
                    error_response = json.dumps(
                        {"error": str(e), "meta": {"status": "error"}}
                    )
                    print(error_response, flush=True)
                    continue

            if tool_name not in agent.tools_manager.tools:
                logging.error(
                    f"Tool '{tool_name}' not found. Available tools: {registered_tools}"
                )
                error_response = json.dumps({"error": f"Tool '{tool_name}' not found."})
                print(error_response, flush=True)
                continue

            # Based on main.py, agent.run takes the whole JSON dict.
            try:
                logging.info(
                    f"Calling agent.run with data for tool '{tool_name}': {input_data}"
                )
                # Use the global main loop to run the async agent.run method
                result = main_loop.run_until_complete(agent.run(input_data))
                logging.info(f"Agent execution finished. Result: {result}")

                # Send result back to stdout
                result_json = json.dumps({"result": result})
                print(result_json, flush=True)
                logging.info(f"Sent result to stdout: {result_json}")

            except Exception as e:
                logging.exception(
                    "Error during agent execution:"
                )  # Log full traceback to stderr
                error_response = json.dumps(
                    {"error": f"Agent execution failed for tool '{tool_name}': {e}"}
                )
                print(error_response, flush=True)  # Output JSON error to stdout

    finally:
        # Close the main loop when done
        if main_loop and not main_loop.is_closed():
            main_loop.close()
            logging.info("Closed main asyncio loop")


async def handle_cursor_document_storage(vectorization_tool, tool_name, input_data):
    """
    Handle Cursor IDE document storage integration.

    Supports JSON inputs like:
    {
        "tool_name": "cursor_save_document",
        "kwargs": {
            "doc_id": "cursor_doc_1",
            "content": "IDE document content",
            "save_dir": "ide_docs",
            "metadata": {"source": "cursor_ide", "timestamp": "2025-01-27T18:30:00Z"}
        }
    }
    """
    kwargs = input_data.get("kwargs", {})

    doc_id = kwargs.get("doc_id")
    content = kwargs.get("content")
    save_dir = kwargs.get("save_dir", "cursor_documents")
    metadata = kwargs.get("metadata", {})

    if not doc_id or not content:
        raise ValueError(
            "cursor_save_document requires 'doc_id' and 'content' in kwargs"
        )

    # Enhance metadata with Cursor integration info
    enhanced_metadata = {
        "source": "cursor_ide",
        "save_directory": save_dir,
        "integration_type": "mcp_stdio",
        "processed_at": input_data.get("timestamp")
        or f"{asyncio.get_event_loop().time()}",
        **metadata,
    }

    # Use vectorization tool to save document to Qdrant and Firestore
    result = await vectorization_tool.vectorize_document(
        doc_id=doc_id,
        content=content,
        metadata=enhanced_metadata,
        tag=f"cursor_{save_dir}",
        update_firestore=True,
    )

    # Add Cursor-specific information to result
    cursor_result = {
        **result,
        "cursor_integration": {
            "save_dir": save_dir,
            "original_doc_id": doc_id,
            "metadata_enhanced": bool(enhanced_metadata),
            "firestore_sync": True,
            "qdrant_tag": f"cursor_{save_dir}",
        },
    }

    logging.info(f"Cursor document storage completed for {doc_id}: {cursor_result}")
    return cursor_result


def handle_qdrant_tool(qdrant_store, tool_name, input_data):
    """Handle QdrantStore-specific tool operations"""
    data = input_data.get("data", {})

    if tool_name == "upsert_vector":
        point_id = data.get("point_id")
        vector = data.get("vector")
        metadata = data.get("metadata", {})

        if not point_id or not vector:
            raise ValueError("upsert_vector requires 'point_id' and 'vector' in data")

        # Use the global main loop if available, otherwise create a temporary one
        if hasattr(qdrant_store, "upsert_vector") and asyncio.iscoroutinefunction(
            qdrant_store.upsert_vector
        ):
            # For real QdrantStore with async methods
            if main_loop and not main_loop.is_closed():
                result = main_loop.run_until_complete(
                    qdrant_store.upsert_vector(point_id, vector, metadata)
                )
            else:
                # Create temporary loop for testing
                temp_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(temp_loop)
                try:
                    result = temp_loop.run_until_complete(
                        qdrant_store.upsert_vector(point_id, vector, metadata)
                    )
                finally:
                    temp_loop.close()
            return {"success": result, "point_id": point_id}
        else:
            # For mock QdrantStore with sync methods
            result = qdrant_store.upsert_vector(point_id, vector, metadata)
            return result

    elif tool_name == "query_vectors_by_tag":
        tag = data.get("tag")
        offset = data.get("offset", 0)
        limit = data.get("limit", 10)

        if not tag:
            raise ValueError("query_vectors_by_tag requires 'tag' in data")

        result = qdrant_store.query_vectors_by_tag(tag, offset, limit)
        return result

    else:
        raise ValueError(f"Unknown QdrantStore tool: {tool_name}")


if __name__ == "__main__":
    main()
