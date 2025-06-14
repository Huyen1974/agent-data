import logging

logger = logging.getLogger(__name__)


def reverse_text(text: str) -> str:
    """Reverses the input string.

    Args:
        text: The string to reverse.

    Returns:
        The reversed string.
    """
    logger.info(f"Executing reverse_text tool with input: '{text}'")
    if not isinstance(text, str):
        logger.warning(f"Invalid input type for reverse_text: {type(text)}")
        # Attempt to convert to string, or raise error
        try:
            text = str(text)
        except Exception:
            raise TypeError("Input must be a string or convertible to a string.")

    reversed_string = text[::-1]
    logger.info(f"reverse_text result: '{reversed_string}'")
    return reversed_string
