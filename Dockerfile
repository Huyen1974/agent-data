FROM python:3.10-slim
WORKDIR /app
COPY . .

# Install build dependencies needed for some packages (like pickle5)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libopenblas-dev libomp5 && rm -rf /var/lib/apt/lists/*

# Install dependencies from requirements.txt
# Includes flask, firestore, gunicorn, etc.
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt --timeout=100
RUN pip install --no-cache-dir -e . --timeout=100

# No explicit EXPOSE needed for Cloud Run when using PORT env var
# EXPOSE 8080

# Set environment variable for the log directory if needed
# ENV LOG_DIR=/app/logs
# RUN mkdir -p $LOG_DIR
ENV PYTHONPATH=/app

# Default Port for Cloud Run
ENV PORT 8080

# Run the web_server module directly using python -m
# This uses the Flask development server (app.run)
# If this works, the issue was related to gunicorn loading
CMD ["python3", "-m", "ADK.agent_data.mcp.web_server"]
# CMD ["python3", "/app/minimal_flask_test.py"] # Reverted diagnostic CMD
