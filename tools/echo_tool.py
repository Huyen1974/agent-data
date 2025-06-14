import logging

logger = logging.getLogger(__name__)


def echo(text_to_echo: str) -> dict:
    """
    A simple tool that echoes back the input text.
    Useful for testing basic agent communication and tool execution flow.

    Args:
        text_to_echo: The string to be echoed back.

    Returns:
        A dictionary with the echoed text under the 'result' key.
    """
    logger.info(f"Executing echo tool with: {text_to_echo}")
    if not isinstance(text_to_echo, str):
        return {"status": "failed", "error": "Input must be a string."}

    return {"status": "success", "result": text_to_echo}
