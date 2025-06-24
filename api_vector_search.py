"""Stub module for api_vector_search to allow test collection."""

from fastapi import FastAPI
from typing import Dict, Any

app = FastAPI()

async def _generate_openai_embedding(text: str, model: str = "text-embedding-ada-002") -> Dict[str, Any]:
    """Stub function for embedding generation."""
    return {
        "embedding": [0.0] * 1536,
        "model": model,
        "text": text
    }

@app.get("/")
async def root():
    return {"message": "Stub API"}
