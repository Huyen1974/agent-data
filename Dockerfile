FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install build dependencies needed for some packages (like pickle5)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    libomp5 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies from requirements.txt
# Includes flask, firestore, gunicorn, etc.
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt --timeout=100

# Copy application code
COPY . .

# Install the package
RUN pip install --no-cache-dir -e . --timeout=100

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Pre-warm Python module cache by importing critical modules
RUN python -c "import sys, logging, json, time, os; \
    from flask import Flask; \
    print('Pre-warmed critical modules')"

# Default Port for Cloud Run
EXPOSE 8080

# Use gunicorn for better production performance instead of Flask dev server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "60", "--preload", "--max-requests", "1000", "ADK.agent_data.mcp.web_server:app"]
