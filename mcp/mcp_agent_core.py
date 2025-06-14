import sys
import os
import json
import logging
import traceback
import time
import asyncio
from typing import Optional, List, Dict, Any, Union, Tuple, cast

# Imports adjusted for Docker structure (/app is root)
from agent.agent_data_agent import AgentDataAgent
from agent_data_manager.tools.register_tools import register_tools

# --- Configuration ---
TOOL_EXECUTION_TIMEOUT_SECONDS = 10.0  # Increased timeout for synchronous execution

# --- Enhanced Logging Setup ---
# Basic setup, assuming configuration might happen elsewhere (like in the Flask app)
# Or configure more robustly here if needed.
logger = logging.getLogger("MCPAgentCore")
# Default handler if no other is configured
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("%(asctime)s [%(request_id)s] %(levelname)-8s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # Add a filter to handle missing request_id
    class RequestIdFilter(logging.Filter):
        def filter(self, record):
            if not hasattr(record, "request_id"):
                record.request_id = "CORE-MSG"
            return True

    handler.addFilter(RequestIdFilter())


# --- Logging Adapter ---
class RequestLogAdapter(logging.LoggerAdapter):
    """Adds 'request_id' and 'duration_ms' to log records via extra."""

    def process(self, msg, kwargs):
        req_id = self.extra.get("request_id", "N/A")
        duration_ms = self.extra.get("duration_ms")
        extra_data = kwargs.get("extra", {})
        extra_data["request_id"] = req_id
        if duration_ms is not None:
            extra_data["duration_ms"] = duration_ms
        kwargs["extra"] = extra_data
        return msg, kwargs


# Default adapter for initialization logs
logger_adapter = RequestLogAdapter(logger, {"request_id": "CORE-INIT"})


# --- Core Agent Class ---
class MCPAgent:
    """Core logic for Minimal Compute Platform Agent. Handles tool execution synchronously."""

    def __init__(self):
        logger_adapter.info("Initializing MCPAgent Core...")
        self.core_agent = AgentDataAgent()
        register_tools(self.core_agent)
        registered_tool_names = list(self.core_agent.tools_manager.tools.keys())
        logger_adapter.info(f"MCPAgent Core initialized. Available tools: {registered_tool_names}")
        self.request_counter = 0

    def _get_next_request_id(self, provided_id=None) -> str:
        """Generates a unique request ID."""
        if provided_id:
            return str(provided_id)
        self.request_counter += 1
        # Use milliseconds for potentially higher uniqueness
        return f"mcp-core-{int(time.time()*1000)}-{self.request_counter}"

    def _create_response(
        self, request_id: str, status: str, result: Any = None, error: Optional[str] = None, meta: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Helper to create a standardized JSON response dictionary."""
        base_meta = meta if meta is not None else {}
        # Ensure standard fields are in meta
        base_meta["request_id"] = request_id
        base_meta["status"] = status

        response = {"result": result, "error": error, "meta": base_meta}
        # Filter None values from top level result/error
        response = {k: v for k, v in response.items() if k == "meta" or v is not None}
        return response

    def _execute_tool_sync(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronously executes a single tool request with error handling."""
        start_time = time.monotonic()
        request_id_in = request_data.get("id")
        # Ensure we have a request ID for logging and response
        request_id = self._get_next_request_id(request_id_in)

        # Initialize local_logger early to use for all subsequent logs in this method
        local_logger = RequestLogAdapter(logger, {"request_id": request_id})

        # Log the entire received request_data
        local_logger.info(f"[_execute_tool_sync] Received request_data: {request_data}")

        tool_name = request_data.get("tool_name")
        # Explicitly name the payload from the request
        input_payload_from_request = request_data.get("input_data", {})

        # Log the extracted input_payload and its type
        local_logger.info(f"[_execute_tool_sync] Extracted input_payload_from_request: {input_payload_from_request}")
        local_logger.info(
            f"[_execute_tool_sync] Type of input_payload_from_request: {type(input_payload_from_request)}"
        )

        response_status = "failed"
        response_error = None
        response_result = None
        duration_ms = None

        try:
            # --- Input Validation ---
            if not tool_name:
                raise ValueError("Missing 'tool_name' in request.")

            # These will be the arguments passed to the tool
            final_args: List[Any] = []
            final_kwargs: Dict[str, Any] = {}  # Initialize as empty dict

            # Check if input_payload_from_request is a dictionary
            if isinstance(input_payload_from_request, dict):
                final_kwargs = input_payload_from_request  # Assign if it's a dict
            else:
                # Log a warning if it's not a dictionary, final_kwargs remains empty
                local_logger.warning(
                    f"Input data for tool {tool_name} is not a dictionary. Using empty kwargs. Received type: {type(input_payload_from_request)}"
                )
                # final_kwargs is already {} as initialized above

            # --- Tool Execution ---
            local_logger.info(f"Executing tool '{tool_name}' with args: {final_args}, kwargs: {final_kwargs}")

            # Add final check log here
            local_logger.info(f"Final check before calling execute_tool - Args: {final_args}, Kwargs: {final_kwargs}")
            # Log before asyncio.run
            local_logger.info(f"Attempting asyncio.run for tool: {tool_name}")
            # Updated to use asyncio.run and argument unpacking
            tool_result_data = asyncio.run(
                self.core_agent.tools_manager.execute_tool(
                    tool_name,  # tool_name is the first positional argument
                    *final_args,  # Unpack final_args list into positional arguments
                    **final_kwargs,  # Unpack final_kwargs dict into keyword arguments
                )
            )
            # Log after asyncio.run and the type of its result
            local_logger.info(f"Completed asyncio.run for tool: {tool_name}. Result type: {type(tool_result_data)}")
            response_status = "success"
            # Assuming execute_tool returns the direct result needed
            response_result = tool_result_data
            local_logger.info(f"Tool '{tool_name}' executed successfully.")

        except (KeyError, ValueError, TypeError) as validation_error:
            response_error = f"Input validation error: {validation_error}"
            local_logger.error(f"{response_error} - Request Data: {request_data}", exc_info=True)
        except Exception as exec_error:
            response_error = f"Tool '{tool_name}' execution error: {exec_error}"
            local_logger.error(f"Error during '{tool_name}' execution.", exc_info=True)

        finally:
            duration_ms = (time.monotonic() - start_time) * 1000
            final_meta = {"duration_ms": round(duration_ms, 2)}
            # Log final outcome (optional, depends on desired log verbosity)
            final_logger_extra = {"request_id": request_id, "duration_ms": round(duration_ms, 2)}
            final_logger = RequestLogAdapter(logger, final_logger_extra)
            if response_status == "success":
                final_logger.info(f"Tool '{tool_name}' completed.")
            else:
                final_logger.error(f"Tool '{tool_name}' failed. Error: {response_error}")

        # Construct final response
        response_data = self._create_response(
            request_id=request_id, status=response_status, result=response_result, error=response_error, meta=final_meta
        )
        return response_data

    def run(self, request_data: Dict, request_id: Optional[str] = None) -> Dict:
        """Processes a single tool request synchronously."""
        exec_request_id = self._get_next_request_id(request_id)
        request_data["id"] = exec_request_id  # Ensure ID is set in the input data

        local_logger = RequestLogAdapter(logger, {"request_id": exec_request_id})
        local_logger.info(f"Processing single request: {request_data.get('tool_name')}")

        if not isinstance(request_data, dict):
            err_msg = "Input must be a single JSON object (dict)."
            local_logger.error(err_msg)
            return self._create_response(exec_request_id, "failed", error=err_msg)

        # Directly execute the single request
        result = self._execute_tool_sync(request_data)
        return result
