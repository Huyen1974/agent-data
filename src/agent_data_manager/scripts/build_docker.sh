#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define variables
IMAGE_NAME="agent-data"
CONTAINER_NAME="agent-data-test"
PORT=8001

# Navigate to the script's directory to ensure context is correct
# Assuming this script is in the 'scripts' directory one level below the Dockerfile
cd "$(dirname "$0")/.."

echo "--- Building Docker image ${IMAGE_NAME}... ---"
docker build -t ${IMAGE_NAME} .

echo "--- Running Docker container ${CONTAINER_NAME} in detached mode... ---"
# Remove existing container with the same name if it exists
docker rm -f ${CONTAINER_NAME} 2>/dev/null || true
docker run -d -p ${PORT}:${PORT} --name ${CONTAINER_NAME} ${IMAGE_NAME}

# Wait for the container/server to start
echo "--- Waiting for server to start (10 seconds)... ---"
sleep 10

echo "--- Testing server endpoint... ---"
# Test with curl - fail if connection refused or HTTP status code is not 2xx/3xx
if curl --fail --silent --show-error http://localhost:${PORT} > /dev/null; then
    echo "✅ Server test successful (curl returned 2xx/3xx)."
else
    echo "❌ Server test failed. Check container logs: docker logs ${CONTAINER_NAME}"
    # Cleanup even on failure
    echo "--- Cleaning up container ${CONTAINER_NAME}... ---"
    docker stop ${CONTAINER_NAME}
    docker rm ${CONTAINER_NAME}
    exit 1
fi

echo "--- Cleaning up container ${CONTAINER_NAME}... ---"
docker stop ${CONTAINER_NAME}
docker rm ${CONTAINER_NAME}

echo "--- Docker build, run, test, and cleanup finished successfully. ---"
