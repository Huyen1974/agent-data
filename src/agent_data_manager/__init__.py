"""
Agent Data Manager - Knowledge Management System for Google Cloud

This package provides a comprehensive knowledge management system built on
Google Cloud infrastructure, featuring:

- Vector storage with Qdrant integration
- Document management and metadata storage
- Authentication and authorization
- RESTful API gateway
- MCP (Model Context Protocol) integration
- Tools for document processing and semantic search
"""

__version__ = "0.1.0"
__author__ = "Agent Data Team"

# Import main components for easy access
try:
    from .agent.agent_data_agent import AgentDataAgent
    from .auth.auth_manager import AuthManager
    from .config.settings import settings
    from .vector_store.firestore_metadata_manager import FirestoreMetadataManager
    from .vector_store.qdrant_store import QdrantStore

    __all__ = [
        "AgentDataAgent",
        "QdrantStore",
        "FirestoreMetadataManager",
        "AuthManager",
        "settings",
        "__version__",
        "__author__",
    ]
except ImportError as e:
    # Allow package to be imported even if some dependencies are missing
    import logging

    logging.warning(f"Some components could not be imported: {e}")
    __all__ = ["__version__", "__author__"]
