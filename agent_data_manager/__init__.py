"""
Compatibility shim for agent_data_manager imports.
This module redirects imports to the actual implementation in ADK.agent_data
"""

# Import all main modules from ADK.agent_data to make them available
# as agent_data_manager.* imports

try:
    # Import core modules
    from ADK.agent_data.config import settings
    from ADK.agent_data import vector_store, tools, auth, config, api
    from ADK.agent_data.vector_store.firestore_metadata_manager import FirestoreMetadataManager
    from ADK.agent_data.vector_store.qdrant_store import QdrantStore
    from ADK.agent_data.auth.auth_manager import AuthManager
    from ADK.agent_data.api_mcp_gateway import app
    
    # Expose modules at package level
    __all__ = [
        'settings',
        'vector_store', 
        'tools',
        'auth',
        'config',
        'api',
        'FirestoreMetadataManager',
        'QdrantStore', 
        'AuthManager',
        'app'
    ]
    
except ImportError as e:
    import logging
    logging.warning(f"Could not import some ADK.agent_data modules: {e}")
    # Allow partial imports to work
    pass 