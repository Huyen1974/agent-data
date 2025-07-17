import logging
from typing import Any

# from agent.base_agent import BaseAgent
# from agent.tools_manager import ToolsManager
# from agent.memory_manager import MemoryManager
from .base_agent import BaseAgent
from .memory_manager import MemoryManager
from .tools_manager import ToolsManager

logger = logging.getLogger(__name__)


class AgentDataAgent(BaseAgent):
    def __init__(self, name: str = "AgentData") -> None:
        super().__init__(name)
        self.tools_manager = ToolsManager(agent_context_ref=self)
        self.memory_manager = MemoryManager()

    async def run(self, input_data: dict[str, Any]) -> Any:
        try:
            logger.info(f"Input to AgentDataAgent.run: {input_data}")
            tool_name = input_data.get("tool_name")
            if not tool_name:
                raise ValueError("tool_name is required in input_data")
            tool_args = input_data.get("args", [])  # Default to empty list if None
            tool_kwargs = input_data.get("kwargs", {})
            logger.info(
                f"Executing tool: {tool_name}, args={tool_args}, kwargs={tool_kwargs}"
            )

            # Ensure args is a list
            if tool_args is None:
                tool_args = []

            return await self.tools_manager.execute_tool(
                tool_name, *tool_args, **tool_kwargs
            )
        except Exception as e:
            logger.error(f"Error inside run(): {e}", exc_info=True)
            # Re-raise the exception to be handled by the caller (e.g., MCPAgent)
            raise e
