# Vector store module compatibility shim
from ADK.agent_data.vector_store import *
from ADK.agent_data.vector_store.base import VectorStore
from ADK.agent_data.vector_store.firestore_metadata_manager import (
    FirestoreMetadataManager,
)
from ADK.agent_data.vector_store.qdrant_store import QdrantStore
