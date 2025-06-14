# Dockerfile for Agent Data
FROM python:3.10.17-slim
WORKDIR /app
COPY requirements.txt .
# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends gcc build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

# Copy application code
COPY ADK ./ADK/
COPY mcp ./mcp/

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
CMD ["python", "mcp/local_mcp_server.py"]
# Test comment to verify edit_file functionality
