import logging
from typing import Any

logger = logging.getLogger(__name__)


def add_numbers(a: int | float, b: int | float) -> dict[str, Any]:
    """Adds two numbers together.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        A dictionary containing the sum under the 'result' key if successful,
        or an error message if inputs are not numbers.
    """
    logger.info(
        f"Executing add_numbers tool with: a={a} ({type(a)}), b={b} ({type(b)})"
    )
    # Input validation
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        logger.error(f"Invalid input types for add_numbers: a={type(a)}, b={type(b)}")
        return {"status": "failed", "error": "Inputs must be numeric (int or float)."}

    # Perform calculation
    try:
        result = a + b
        logger.info(f"add_numbers calculation result: {result}")
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error during addition in add_numbers: {e}", exc_info=True)
        return {"status": "failed", "error": f"Calculation error: {e}"}
