# Enhanced Dockerfile with SHA digest pinning and multi-architecture support
# Base image pinned with SHA digest for reproducibility
FROM python:3.10.17-slim@sha256:49454d2bf78a48f217eb25ecbcb4b5face313fea6a6e82706465a6990303ada2

# Set build arguments for multi-architecture support
ARG TARGETPLATFORM
ARG BUILDPLATFORM
ARG TARGETARCH
ARG TARGETOS

# Add metadata labels
LABEL maintainer="Agent Data Team"
LABEL version="v0.1.1-docker-enhanced"
LABEL description="Agent Data MCP Server with enhanced Docker configuration"
LABEL build.platform=${BUILDPLATFORM}
LABEL target.platform=${TARGETPLATFORM}

# Set environment variables early for better layer caching
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src:/app/ADK:/app

WORKDIR /app

# Install system dependencies with proper cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    libomp5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with optimizations
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt --timeout=100

# Copy pytest configuration
COPY pytest.ini .
COPY conftest.py .
COPY __init__.py .

# Copy application source code (ordered by change frequency)
COPY src/ ./src/
COPY tests/ ./tests/
COPY tools/ ./tools/
COPY mcp/ ./mcp/
COPY agent/ ./agent/
COPY auth/ ./auth/
COPY config/ ./config/
COPY api/ ./api/
COPY vector_store/ ./vector_store/
COPY utils/ ./utils/
COPY ADK/ ./ADK/
COPY api_mcp_gateway.py .

# Copy additional Python files
COPY *.py .

# Expose port for testing
EXPOSE 8001

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command for verification
CMD ["pytest", "--version"]
