"""
Agent Data Langroid Server - FastAPI server for agent data operations
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Agent Data Langroid",
    description="Multi-agent knowledge management system built with Langroid framework",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    version: str
    langroid_available: bool


class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class MessageResponse(BaseModel):
    response: str
    session_id: Optional[str] = None


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with health check."""
    try:
        from agent_data import get_info
        info = get_info()
        
        return HealthResponse(
            status="healthy",
            version=info["version"],
            langroid_available=info["langroid_available"]
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return await root()


@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """Chat endpoint for agent interactions."""
    try:
        # Basic echo response for now
        response = f"Echo: {request.message}"
        
        # TODO: Integrate with Langroid agents here
        
        return MessageResponse(
            response=response,
            session_id=request.session_id
        )
    except Exception as e:
        logger.error(f"Chat endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed")


@app.get("/info")
async def info():
    """Get detailed system information."""
    try:
        from agent_data import get_info
        return get_info()
    except Exception as e:
        logger.error(f"Info endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Unable to get system info")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 