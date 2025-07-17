# Multi-stage Docker build for MCP Gateway - Optimized for size <500MB
# Stage 1: Build stage with all dependencies
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy optimized runtime requirements
COPY ADK/agent_data/docker/requirements.runtime.txt /tmp/requirements.runtime.txt

# Install only runtime dependencies
RUN pip install --no-cache-dir --timeout=600 -r /tmp/requirements.runtime.txt

# Stage 2: Runtime stage (minimal)
FROM python:3.11-slim as runtime

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy only essential application code
COPY ADK/agent_data/api_mcp_gateway.py ./ADK/agent_data/
COPY ADK/agent_data/local_mcp_server.py ./ADK/agent_data/
COPY ADK/agent_data/mcp/ ./ADK/agent_data/mcp/
COPY ADK/agent_data/utils/ ./ADK/agent_data/utils/
COPY ADK/agent_data/vector_store/ ./ADK/agent_data/vector_store/
COPY ADK/agent_data/config/ ./ADK/agent_data/config/
COPY ADK/agent_data/auth/ ./ADK/agent_data/auth/
COPY ADK/agent_data/agent/ ./ADK/agent_data/agent/
COPY ADK/agent_data/tools/ ./ADK/agent_data/tools/
COPY ADK/agent_data/api/ ./ADK/agent_data/api/
COPY ADK/agent_data/__init__.py ./ADK/agent_data/
COPY conftest.py ./

# Set environment variables
ENV PORT=8080
ENV HOST=0.0.0.0
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the MCP Gateway
CMD ["python", "-m", "ADK.agent_data.api_mcp_gateway"]
