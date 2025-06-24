"""Stub module for cs_agent_api to allow test collection."""

from fastapi import FastAPI
from typing import Any


app = FastAPI()


def get_firestore_manager() -> Any:
    """Stub function to get firestore manager."""
    from .vector_store.firestore_metadata_manager import FirestoreMetadataManager
    return FirestoreMetadataManager()


@app.get("/")
async def root():
    return {"message": "Stub CS Agent API"}
