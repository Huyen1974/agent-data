import logging

logger = logging.getLogger(__name__)


def multiply_numbers(**kwargs) -> dict:
    """Multiplies two numbers provided as keyword arguments.
    Accepts either {'x': val1, 'y': val2} or {'a': val1, 'b': val2}.

    Args:
        **kwargs: Keyword arguments containing the numbers.

    Returns:
        A dictionary with the multiplication result or an error.
    """
    logger.info(f"Executing multiply_numbers tool with kwargs: {kwargs}")

    # Determine which keys were provided
    if "x" in kwargs and "y" in kwargs:
        num1_key, num2_key = "x", "y"
    elif "a" in kwargs and "b" in kwargs:
        num1_key, num2_key = "a", "b"
    else:
        error_msg = "Input must contain either keys ('x', 'y') or ('a', 'b')."
        logger.error(error_msg)
        return {"status": "failed", "error": error_msg}

    num1 = kwargs[num1_key]
    num2 = kwargs[num2_key]

    if not isinstance(num1, (int, float)) or not isinstance(num2, (int, float)):
        error_msg = (
            f"Inputs must be numbers. Received {num1_key}={num1} ({type(num1)}), {num2_key}={num2} ({type(num2)})."
        )
        logger.error(error_msg)
        return {"status": "failed", "error": error_msg}

    result = num1 * num2
    logger.info(f"Calculation: {num1} * {num2} = {result}")
    return {"status": "success", "result": result}
