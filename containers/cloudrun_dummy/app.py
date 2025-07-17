"""
Dummy Cloud Run application for CI/CD testing.
Built with FastAPI and designed for agent data integration testing.
"""

import os
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# Pydantic models for request/response
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str
    version: str
    environment: str


class AgentDataRequest(BaseModel):
    query: str
    agent_id: str | None = None
    metadata: dict[str, Any] | None = None


class AgentDataResponse(BaseModel):
    agent_id: str
    query: str
    response: str
    confidence: float
    processing_time_ms: int
    timestamp: str


# Initialize FastAPI app
app = FastAPI(
    title="Agent Data Langroid - Dummy Cloud Run Service",
    description="Dummy service for CI/CD testing of agent data management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "agent-data-langroid-dummy",
        "version": "1.0.0",
        "description": "Dummy Cloud Run service for agent data testing",
        "endpoints": {
            "health": "/health",
            "agent": "/agent",
            "query": "/query",
            "metrics": "/metrics",
            "docs": "/docs",
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for load balancer."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        service="cloudrun_dummy",
        version="1.0.0",
        environment=os.environ.get("ENV", "development"),
    )


@app.get("/agent")
async def get_agent_info():
    """Get dummy agent information."""
    return {
        "agent_id": "dummy_agent_cloudrun",
        "status": "active",
        "capabilities": [
            "semantic_search",
            "document_processing",
            "vector_operations",
            "knowledge_management",
            "query_routing",
        ],
        "frameworks": {
            "langroid": "0.58.x",
            "fastapi": "0.104.x",
            "qdrant": "available",
        },
        "performance": {
            "avg_response_time_ms": 234,
            "queries_per_second": 45,
            "uptime_hours": 24,
            "memory_usage_mb": 512,
        },
    }


@app.post("/query", response_model=AgentDataResponse)
async def process_query(request: AgentDataRequest):
    """Process a dummy agent data query."""
    start_time = datetime.utcnow()

    # Simulate processing
    dummy_responses = [
        "This is a simulated response from the agent data system.",
        "The dummy agent has processed your query successfully.",
        "Here's some mock data for your query about agent capabilities.",
        "The vector search returned relevant results from the knowledge base.",
        "Agent data processing complete with high confidence.",
    ]

    # Simple hash-based response selection for consistency
    response_idx = hash(request.query) % len(dummy_responses)
    response_text = dummy_responses[response_idx]

    # Calculate processing time
    end_time = datetime.utcnow()
    processing_time = (end_time - start_time).total_seconds() * 1000

    return AgentDataResponse(
        agent_id=request.agent_id or "dummy_agent_cloudrun",
        query=request.query,
        response=response_text,
        confidence=0.85 + (hash(request.query) % 15) / 100,  # 0.85 - 0.99
        processing_time_ms=int(processing_time),
        timestamp=end_time.isoformat(),
    )


@app.get("/metrics")
async def get_metrics():
    """Get dummy service metrics."""
    return {
        "service_metrics": {
            "requests_total": 1247,
            "requests_per_minute": 12,
            "avg_response_time_ms": 187,
            "error_rate": 0.02,
            "uptime_seconds": 86400,
        },
        "agent_metrics": {
            "active_agents": 3,
            "queries_processed": 892,
            "knowledge_items": 15420,
            "vector_dimensions": 768,
            "index_size_mb": 245,
        },
        "resource_metrics": {
            "cpu_usage_percent": 23.4,
            "memory_usage_mb": 512,
            "disk_usage_mb": 128,
            "network_io_kb": 1024,
        },
    }


@app.get("/simulate-error")
async def simulate_error():
    """Endpoint to test error handling."""
    raise HTTPException(
        status_code=500, detail="This is a simulated error for testing purposes"
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = datetime.utcnow()
    response = await call_next(request)
    process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    response.headers["X-Process-Time-MS"] = str(int(process_time))
    return response


if __name__ == "__main__":
    # For local development
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
