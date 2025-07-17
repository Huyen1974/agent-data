import inspect
import json
import logging

# Ensure parent directory (ADK/agent_data) is in path if run directly
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import necessary components using relative paths
try:
    from agent_data_manager.tools.register_tools import (
        get_all_tool_functions,
    )  # Use the new helper
except ImportError as e:
    logger.error(f"Failed to import tools using relative paths: {e}", exc_info=True)
    sys.exit(1)

# --- Tool Registration ---
# Use the helper function to get all available tools
# This dictionary holds {tool_name: function_object}
ALL_TOOLS = get_all_tool_functions()
logger.info(f"Discovered tools: {list(ALL_TOOLS.keys())}")


def run_mcp_loop():
    logger.info("MCP Stdio Server Started. Waiting for JSON input on stdin...")
    while True:
        line = sys.stdin.readline()  # Read one line at a time
        if not line:
            # Handle EOF or empty line if desired. Currently, it breaks the loop.
            logger.info("Stdin stream ended or received empty line. Exiting loop.")
            break

        request = {}
        response = {}
        request_id = None
        start_time = time.time()

        try:
            request = json.loads(line)
            request_id = request.get("meta", {}).get("request_id")
            logger.debug(f"Received request (ID: {request_id}): {request}")

            # Handle exit command *after* successful parsing
            if request.get("action") == "exit":
                logger.info(f"Exit command received (ID: {request_id}). Shutting down.")
                response = {
                    "result": "Exiting server gracefully.",
                    "meta": {"status": "success", "request_id": request_id},
                    "error": None,
                }
                print(json.dumps(response), flush=True)
                break  # Exit the while loop cleanly

            # --- Tool Execution ---
            tool_name = request.get("tool")
            tool_input = request.get("input")

            if not tool_name:
                logger.error(f"Missing 'tool' key in request (ID: {request_id})")
                response = {
                    "result": None,
                    "meta": {"status": "error", "request_id": request_id},
                    "error": "Missing 'tool' key in request",
                }
            elif tool_name not in ALL_TOOLS:
                logger.error(f"Unknown tool requested (ID: {request_id}): {tool_name}")
                response = {
                    "result": None,
                    "meta": {"status": "error", "request_id": request_id},
                    "error": f"Unknown tool: {tool_name}",
                }
            else:
                try:
                    tool_function = ALL_TOOLS[tool_name]
                    logger.info(
                        f"Executing tool '{tool_name}' (ID: {request_id}) with input: {tool_input}"
                    )

                    # --- START REPLACEMENT: Signature-based tool execution ---
                    tool_result_data = None
                    try:
                        sig = inspect.signature(tool_function)
                        params = sig.parameters

                        # Determine how to call based on input and signature
                        if tool_name == "get_registered_tools":  # Specific case
                            tool_result_data = tool_function()  # Call without arguments
                        elif isinstance(tool_input, dict):
                            # If input is dict, try to match kwargs
                            try:
                                tool_result_data = tool_function(**tool_input)
                            except TypeError as e:
                                # If kwargs fail AND the function expects exactly 1 positional arg?
                                if len(params) == 1 and list(params.values())[
                                    0
                                ].kind in [
                                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                                    inspect.Parameter.POSITIONAL_ONLY,
                                ]:
                                    logger.debug(
                                        f"kwargs failed for {tool_name}, trying as single arg: {e}"
                                    )
                                    tool_result_data = tool_function(tool_input)
                                else:
                                    raise e  # Re-raise original TypeError if fallback doesn't match signature
                        elif isinstance(tool_input, list):
                            # If input is list, try to match positional args
                            tool_result_data = tool_function(*tool_input)
                        elif tool_input is None:
                            # If input is None, try calling with no args
                            tool_result_data = tool_function()
                        else:
                            # Fallback: try calling with input as single argument
                            tool_result_data = tool_function(tool_input)

                    except Exception as exec_err:
                        # Catch any exception during signature inspection or execution
                        logger.error(
                            f"Error executing tool '{tool_name}' (ID: {request_id}): {exec_err}",
                            exc_info=True,
                        )
                        # Raise it to be handled by the outer try-except block
                        raise exec_err
                    # --- END REPLACEMENT ---

                    # Standardize response structure
                    response = {
                        "result": None,  # Default to None
                        "meta": {
                            "status": "success",
                            "request_id": request_id,
                        },  # Default to success
                        "error": None,  # Default to None
                    }

                    # Process tool result
                    if (
                        isinstance(tool_result_data, dict)
                        and "status" in tool_result_data
                    ):
                        if tool_result_data["status"] == "failed":
                            response["meta"]["status"] = "error"
                            response["error"] = tool_result_data.get(
                                "error",
                                "Tool reported failure without specific error message.",
                            )
                            response["result"] = tool_result_data.get(
                                "result"
                            )  # Keep result even on failure if provided
                            logger.warning(
                                f"Tool '{tool_name}' reported failure (ID: {request_id}): {response['error']}"
                            )
                        elif tool_result_data["status"] == "success":
                            response["result"] = tool_result_data.get(
                                "result"
                            )  # Extract result from successful dict
                        else:  # Handle unexpected status values if needed
                            response["result"] = (
                                tool_result_data  # Pass through if status is unrecognized but dict is structured
                            )
                            logger.warning(
                                f"Tool '{tool_name}' returned dict with unrecognized status: {tool_result_data['status']}"
                            )
                    else:
                        # If tool result is not a dict with status, assume success and use it as the result
                        response["result"] = tool_result_data

                    if response["meta"]["status"] == "success":
                        logger.info(
                            f"Tool '{tool_name}' executed successfully (ID: {request_id})."
                        )

                except Exception as e:
                    logger.error(
                        f"Error executing tool '{tool_name}' (ID: {request_id}): {e}",
                        exc_info=True,
                    )
                    response["result"] = None
                    response["meta"] = {"status": "error", "request_id": request_id}
                    response["error"] = (
                        f"Error in tool '{tool_name}': {type(e).__name__}: {e}"
                    )

            # Add duration and send response
            duration = (time.time() - start_time) * 1000
            if "meta" not in response:
                response["meta"] = {}  # Ensure meta exists
            response["meta"]["duration_ms"] = duration
            response["meta"]["request_id"] = request_id  # Ensure request_id is set

            print(json.dumps(response), flush=True)
            logger.debug(f"Sent response (ID: {request_id}): {response}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {line.strip()}")
            error_response = {
                "result": None,
                "meta": {
                    "status": "error",
                    "request_id": None,
                },  # request_id might not be available if JSON is invalid
                "error": "Invalid JSON input",
            }
            print(json.dumps(error_response), flush=True)
            # Continue to the next iteration to wait for more input
            continue
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting.")
            break  # Exit loop on Ctrl+C
        except Exception as e:
            # Catch any other unexpected errors in the main loop
            logger.error(f"Unhandled error in MCP loop: {e}", exc_info=True)
            try:
                # Try to send a fatal error response if possible
                fatal_response = {
                    "result": None,
                    "meta": {
                        "status": "fatal",
                        "request_id": request_id,
                    },  # Use request_id if available
                    "error": f"Unhandled server error: {type(e).__name__}: {e}",
                }
                print(json.dumps(fatal_response), flush=True)
            except Exception as print_err:
                # If even printing the error fails, log it and exit
                logger.error(f"Failed to send fatal error response: {print_err}")
            break  # Exit loop on fatal error

    # This code runs after the loop breaks (e.g., on exit command, EOF, interrupt, or fatal error)
    logger.info("MCP Stdio Server loop finished.")


if __name__ == "__main__":
    logger.info("Starting MCP Stdio Server...")
    run_mcp_loop()
    logger.info("MCP Stdio Server Stopped.")
    sys.exit(0)  # Ensure exit code 0 on normal termination
