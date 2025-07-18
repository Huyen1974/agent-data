"""FastAPI server for Agent Data system."""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agent Data API",
    description="Knowledge management system for AI agents",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Agent Data API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        # Basic health checks
        checks = {
            "api": "ok",
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        }

        # TODO: Add more health checks for:
        # - Qdrant connectivity
        # - Firestore connectivity
        # - OpenAI API availability

        return {"status": "healthy", "checks": checks}

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy") from e


@app.post("/chat")
async def chat(message: dict):
    """Chat endpoint for agent interactions."""
    try:
        # TODO: Implement actual chat functionality
        user_message = message.get("message", "")

        response = {
            "response": f"Echo: {user_message}",
            "status": "ok",
        }

        return response

    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed") from e


@app.get("/info")
async def info():
    """System information endpoint."""
    try:
        return {
            "system": "Agent Data",
            "version": "1.0.0",
            "python_version": sys.version,
            "features": [
                "Vector search",
                "Document management",
                "AI agent integration",
            ],
        }
    except Exception as e:
        logger.error(f"Info endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to get system info") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
