# from agent_toolkit.tool import tool # Removed problematic import


# @tool("error_tool") # Removed decorator
def raise_error_tool():
    """
    This tool intentionally raises a RuntimeError for testing purposes.
    """
    raise RuntimeError("Intentional error for test.")


# Example usage (for testing purposes, typically not included in the final tool)
if __name__ == "__main__":
    try:
        raise_error_tool()
    except RuntimeError as e:
        print(f"Caught expected error: {e}")
