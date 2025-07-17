import asyncio
import inspect
import logging
from typing import Any

# Forward declaration for type hinting if AgentDataAgent is in a separate file and causes circular import
# For example:
# class AgentDataAgent: ... (or use \'AgentDataAgent\' as a string literal in type hints)

logger = logging.getLogger(__name__)


class ToolsManager:
    def __init__(self, agent_context_ref: Any):  # Changed to accept agent_context_ref
        self.tools: dict[str, dict[str, Any]] = (
            {}
        )  # To store function and pass_context flag
        self.agent_context_ref = agent_context_ref  # Store the agent reference

    def register_tool(
        self, name: str, tool_function: Any, pass_agent_context: bool = False
    ) -> None:  # Added pass_agent_context
        logger.info(
            f"ToolsManager: Registering tool '{name}'. Pass context: {pass_agent_context}"
        )
        self.tools[name] = {
            "function": tool_function,
            "pass_context": pass_agent_context,
        }

    async def execute_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Any:
        logger.info(f"ToolsManager: Attempting to get tool with name: '{tool_name}'")
        if tool_name not in self.tools:
            logger.error(f"Tool '{tool_name}' not found during execution attempt.")
            raise ValueError(f"Tool '{tool_name}' not found")

        tool_info = self.tools[tool_name]
        tool_func = tool_info["function"]
        should_pass_context = tool_info["pass_context"]

        final_args = list(args)
        if should_pass_context:
            if self.agent_context_ref is None:
                logger.error(
                    f"Tool '{tool_name}' requires agent_context, but agent_context_ref is None in ToolsManager."
                )
                raise ValueError(f"Agent context not available for tool '{tool_name}'")
            final_args.insert(0, self.agent_context_ref)
            logger.info(
                f"ToolsManager: Prepending agent_context for tool '{tool_name}'."
            )

        logger.info(f"ToolsManager: Retrieved tool object: {tool_func}")
        logger.info(f"ToolsManager: Type of tool object: {type(tool_func)}")
        try:
            logger.info(
                f"ToolsManager: Name of tool object (tool_func.__name__): {tool_func.__name__}"
            )
        except AttributeError:
            logger.info("ToolsManager: Tool object does not have __name__ attribute.")
        try:
            logger.info(
                f"ToolsManager: Signature of tool object (inspect.signature(tool_func)): {inspect.signature(tool_func)}"
            )
        except Exception as e:
            logger.info(
                f"ToolsManager: Could not get signature of tool object. Error: {e}"
            )

        logger.info(
            f"ToolsManager: Executing tool '{tool_name}' internally with final_args: {final_args}, kwargs: {kwargs}"
        )

        try:
            if asyncio.iscoroutinefunction(tool_func):
                return await tool_func(*final_args, **kwargs)
            else:
                # Run synchronous functions in an executor to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, lambda: tool_func(*final_args, **kwargs)
                )
        except Exception as e:
            logger.error(
                f"ToolsManager: Error executing tool '{tool_name}'. Args: {final_args}, Kwargs: {kwargs}. Error: {e}",
                exc_info=True,
            )
            raise
