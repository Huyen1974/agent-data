import logging
import os
import sys
import time

from .mcp_agent_core import MCPAgent

# --- Path Setup ---
# Add project root to sys.path to ensure absolute imports work when run as script
script_dir_import = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir_import, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Logging Setup (Direct to stderr) ---
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.INFO, format=LOG_FORMAT, stream=sys.stderr
)  # Configure root logger to use stderr
logger = logging.getLogger("MCPAgentScript")


# Custom adapter (optional, could be simplified if only logging to stderr)
class RequestLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        req_id = self.extra.get("request_id")
        if req_id:
            return f"[{req_id}] {msg}", kwargs
        else:
            return msg, kwargs


logger_adapter = RequestLogAdapter(logger, {"request_id": "SCRIPT-INIT"})

# --- Import Core Agent (Using Absolute Import) ---
# The import 'from .mcp_agent_core import MCPAgent' at the top of the file is sufficient
# and correct for package-based imports. Removing the redundant/problematic try-except block.

# --- Synchronous Request Processing Function ---


def process_request(agent: MCPAgent, request_data: dict) -> dict:
    """Processes a single MCP request synchronously."""
    tool_name = request_data.get("tool_name")
    input_data = request_data.get("input_data", {})
    # Use provided id or generate one based on time
    request_id = request_data.get(
        "id", f"req-{int(time.time()*1000)}"
    )  # Added ms precision

    # Create a logger adapter for this request if needed, or just log directly
    local_logger = logging.LoggerAdapter(logger, {"request_id": request_id})
    local_logger.info(
        f"Processing request: tool='{tool_name}', input_data={input_data}"
    )

    if not tool_name:
        local_logger.error(f"Missing 'tool_name' in payload: {request_data}")
        return {
            "error": "Missing 'tool_name' in request payload",
            "meta": {"status": "error", "request_id": request_id},
        }

    try:
        # Pass request_id to the agent's run method
        # Ensure the agent.run method is synchronous or handled appropriately if it starts async tasks internally
        result = agent.run(
            {"tool_name": tool_name, "input_data": input_data}, request_id=request_id
        )
        local_logger.info(
            f"Successfully executed tool '{tool_name}'. Result keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
        )
        # Ensure the result includes the request_id in its metadata if agent.run doesn't add it
        if (
            isinstance(result, dict)
            and "meta" in result
            and "request_id" not in result["meta"]
        ):
            result["meta"]["request_id"] = request_id
        elif isinstance(result, dict) and "meta" not in result:
            result["meta"] = {
                "status": "success",
                "request_id": request_id,
            }  # Add basic meta if missing
        return result
    except Exception as e:
        # Log the full traceback for exceptions during tool execution
        local_logger.error(
            f"Error executing tool '{tool_name}': {str(e)}", exc_info=True
        )
        # Return a structured error response
        return {
            "error": f"Error executing tool '{tool_name}': {str(e)}",
            "meta": {"status": "error", "request_id": request_id},
        }


# --- End of Synchronous Function ---

# Removed the old async def process_request_str_async(...) function
# Removed the old async def run_loop_async(...) function
# Removed the old if __name__ == "__main__": block with asyncio.run(...)

# Optional: Example synchronous execution for direct testing
# if __name__ == "__main__":
#     print("Running mcp_agent.py directly for testing...")
#     test_agent = MCPAgent()
#     # Example 1: Echo tool
#     test_request_echo = {"tool_name": "echo", "args": ["Hello Synchronous Direct"], "id": "test-sync-direct-1"}
#     print(f"Testing with: {test_request_echo}")
#     test_response_echo = process_request(test_agent, test_request_echo)
#     print(f"Response: {json.dumps(test_response_echo)}")
#     # Example 2: Invalid tool
#     test_request_invalid = {"tool_name": "nonexistent", "args": [], "id": "test-sync-direct-2"}
#     print(f"Testing with: {test_request_invalid}")
#     test_response_invalid = process_request(test_agent, test_request_invalid)
#     print(f"Response: {json.dumps(test_response_invalid)}")
#     print("Direct testing finished.")
