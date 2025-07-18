"""
Agent Data Langroid - Multi-agent knowledge management system.

Built with Langroid framework for advanced AI agent orchestration.
"""

__version__ = "0.1.0"
__author__ = "Agent Data Team"
__email__ = "team@agentdata.com"

# Core imports for easy access
try:
    import langroid as lr
    from langroid import ChatAgent, Task
    from langroid.language_models import OpenAIGPTConfig

    # Get version using importlib.metadata
    try:
        from importlib.metadata import version

        LANGROID_VERSION = version("langroid")
    except ImportError:
        # Fallback for Python < 3.8
        import pkg_resources

        LANGROID_VERSION = pkg_resources.get_distribution("langroid").version
    except Exception:
        LANGROID_VERSION = "unknown"

    # Mark as available
    LANGROID_AVAILABLE = True

except ImportError:
    # Graceful fallback if langroid is not available
    LANGROID_AVAILABLE = False
    LANGROID_VERSION = None


def get_version():
    """Get the version of the agent-data-langroid package."""
    return __version__


def check_dependencies():
    """Check if all required dependencies are available."""
    dependencies = {
        "langroid": LANGROID_AVAILABLE,
        "fastapi": True,  # Will be checked by imports
        "uvicorn": True,
        "pydantic": True,
        "openai": True,
        "qdrant_client": True,
    }

    try:
        import fastapi
        import openai
        import pydantic
        import qdrant_client
        import uvicorn
    except ImportError as e:
        dependencies[str(e).split("'")[1]] = False

    return dependencies


def get_info():
    """Get package information."""
    info = {
        "name": "agent-data-langroid",
        "version": __version__,
        "author": __author__,
        "email": __email__,
        "langroid_available": LANGROID_AVAILABLE,
        "langroid_version": LANGROID_VERSION,
        "dependencies": check_dependencies(),
    }
    return info
