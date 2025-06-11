# Minimal mock decorator to resolve import errors
import functools


def tool(name=None):  # Allow optional name argument like the real decorator might
    def decorator(func):
        # Here you could potentially add metadata to the function
        # e.g., func._tool_name = name or func.__name__
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    # Handle cases where @tool is used without () vs with (@tool())
    if callable(name):
        # Used as @tool without arguments
        func = name
        name = None
        return decorator(func)
    else:
        # Used as @tool(name=...) or @tool()
        return decorator
