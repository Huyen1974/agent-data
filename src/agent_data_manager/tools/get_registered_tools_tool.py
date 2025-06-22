import logging
from typing import Dict, Any

# from agent_data_manager.agent.agent_data_agent import AgentDataAgent # For type hint, if safe

logger = logging.getLogger(__name__)


# def get_registered_tools(available_tools: Dict[str, Any]) -> Dict[str, Any]: # Old signature
def get_registered_tools(agent_context: Any) -> Dict[str, Any]:  # New signature
    """Returns a list of all registered tool names from the agent's ToolsManager."""
    logger.info("Executing get_registered_tools tool via agent_context")
    try:
        if not hasattr(agent_context, "tools_manager") or not hasattr(agent_context.tools_manager, "tools"):
            logger.error("agent_context does not have 'tools_manager' or 'tools_manager.tools'")
            return {"status": "failed", "error": "Invalid agent_context structure"}

        tool_names = list(agent_context.tools_manager.tools.keys())
        logger.info(f"Found registered tools via agent_context: {tool_names}")
        return {"status": "success", "result": tool_names}
    except Exception as e:
        logger.error(f"Error getting registered tools via agent_context: {e}", exc_info=True)
        return {"status": "failed", "error": f"Error getting tool list: {e}"}
