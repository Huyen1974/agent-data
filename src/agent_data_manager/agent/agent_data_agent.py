import logging

from ..session.session_manager import get_session_manager

# from agent.base_agent import BaseAgent
# from agent.tools_manager import ToolsManager
# from agent.memory_manager import MemoryManager
from .base_agent import BaseAgent
from .memory_manager import MemoryManager
from .tools_manager import ToolsManager

logger = logging.getLogger(__name__)


class AgentDataAgent(BaseAgent):
    def __init__(self, name="AgentData"):
        super().__init__(name)
        self.tools_manager = ToolsManager(agent_context_ref=self)
        self.memory_manager = MemoryManager()
        self.session_manager = get_session_manager()
        self.current_session_id: str | None = None

    async def run(self, input_data):
        try:
            logger.info(f"Input to AgentDataAgent.run: {input_data}")

            # Extract session ID if provided
            session_id = input_data.get("session_id")
            if session_id:
                self.current_session_id = session_id
                logger.debug(f"Set current session ID: {session_id}")

            tool_name = input_data.get("tool_name")
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

    async def create_session(self, initial_state: dict | None = None) -> dict:
        """Create a new session and set it as current."""
        try:
            result = await self.session_manager.create_session(
                initial_state=initial_state
            )
            if result.get("status") == "success":
                self.current_session_id = result.get("session_id")
                logger.info(
                    f"Created and set current session: {self.current_session_id}"
                )
            return result
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return {"status": "failed", "error": str(e)}

    async def get_current_session(self) -> dict | None:
        """Get the current session data."""
        if not self.current_session_id:
            return None
        try:
            return await self.session_manager.get_session(self.current_session_id)
        except Exception as e:
            logger.error(f"Failed to get current session: {e}")
            return None

    async def update_session_state(self, state_update: dict) -> dict:
        """Update the current session state."""
        if not self.current_session_id:
            return {"status": "failed", "error": "No current session set"}
        try:
            return await self.session_manager.update_session_state(
                self.current_session_id, state_update
            )
        except Exception as e:
            logger.error(f"Failed to update session state: {e}")
            return {"status": "failed", "error": str(e)}

    async def close_session(self) -> dict:
        """Close the current session."""
        if not self.current_session_id:
            return {"status": "failed", "error": "No current session set"}
        try:
            result = await self.session_manager.delete_session(self.current_session_id)
            if result.get("status") == "success":
                self.current_session_id = None
                logger.info("Closed current session")
            return result
        except Exception as e:
            logger.error(f"Failed to close session: {e}")
            return {"status": "failed", "error": str(e)}
