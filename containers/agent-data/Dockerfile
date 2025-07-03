# Dockerfile for Agent Data Project
# Optimized for MacBook M1 with fast build times
FROM python:3.10.17-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src:/app/ADK:/app

# Install system dependencies (minimal for M1 compatibility)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies with timeout for M1 stability
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copy project configuration files
COPY pytest.ini .
COPY conftest.py .
COPY __init__.py .

# Copy all project directories
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

# Copy other essential files
COPY api_mcp_gateway.py .
COPY *.py .

# Expose port for API if needed
EXPOSE 8001

# Default command to run pytest
CMD ["pytest", "--version"]
