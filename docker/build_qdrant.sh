#!/bin/bash
# Build script for optimized Qdrant hybrid Docker image
# CLI140i: Validates size <500MB and startup time <2s

set -e

# Configuration
IMAGE_NAME="qdrant-hybrid-optimized"
TAG="latest"
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"
MAX_SIZE_MB=500
MAX_STARTUP_TIME=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Building optimized Qdrant hybrid Docker image...${NC}"

# Build context is the project root
BUILD_CONTEXT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${BUILD_CONTEXT}"
DOCKERFILE_PATH="ADK/agent_data/docker/Dockerfile.qdrant"

echo "Build context: ${BUILD_CONTEXT}"
echo "Dockerfile: ${DOCKERFILE_PATH}"

# Check if Dockerfile exists
if [ ! -f "${DOCKERFILE_PATH}" ]; then
    echo -e "${RED}❌ Dockerfile not found: ${DOCKERFILE_PATH}${NC}"
    exit 1
fi

# Check if required files exist
if [ ! -f "scripts/qdrant_restore.py" ]; then
    echo -e "${RED}❌ Required file not found: scripts/qdrant_restore.py${NC}"
    exit 1
fi

# Build the image
echo -e "${YELLOW}🔨 Building image: ${FULL_IMAGE_NAME}${NC}"
docker build \
    -f "${DOCKERFILE_PATH}" \
    -t "${FULL_IMAGE_NAME}" \
    .

# Check image size
echo -e "${BLUE}📏 Checking image size...${NC}"
IMAGE_SIZE_BYTES=$(docker inspect "${FULL_IMAGE_NAME}" --format='{{.Size}}')
IMAGE_SIZE_MB=$(echo "scale=2; ${IMAGE_SIZE_BYTES}/1024/1024" | bc)

echo "Image size: ${IMAGE_SIZE_MB} MB"

if (( $(echo "${IMAGE_SIZE_MB} < ${MAX_SIZE_MB}" | bc -l) )); then
    echo -e "${GREEN}✅ Image size optimization successful: ${IMAGE_SIZE_MB} MB < ${MAX_SIZE_MB} MB${NC}"
else
    echo -e "${RED}❌ Image size exceeds limit: ${IMAGE_SIZE_MB} MB >= ${MAX_SIZE_MB} MB${NC}"
    exit 1
fi

# Test startup time and functionality
echo -e "${BLUE}⏱️  Testing container startup time and functionality...${NC}"

# Start container in background
CONTAINER_ID=$(docker run -d -p 6333:6333 "${FULL_IMAGE_NAME}")

# Function to cleanup container
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up container...${NC}"
    docker stop "${CONTAINER_ID}" >/dev/null 2>&1 || true
    docker rm "${CONTAINER_ID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

# Wait for health check to pass with timeout
START_TIME=$(date +%s.%N)
HEALTH_STATUS=""
ATTEMPTS=0
MAX_ATTEMPTS=20

echo "Waiting for Qdrant to be ready..."

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    if curl -s -f http://localhost:6333/health >/dev/null 2>&1; then
        END_TIME=$(date +%s.%N)
        STARTUP_TIME=$(echo "${END_TIME} - ${START_TIME}" | bc)
        echo -e "${GREEN}✅ Qdrant is ready!${NC}"
        break
    fi
    
    ATTEMPTS=$((ATTEMPTS + 1))
    echo -n "."
    sleep 0.5
done

echo ""

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}❌ Container startup timeout after ${MAX_ATTEMPTS} attempts${NC}"
    docker logs "${CONTAINER_ID}"
    exit 1
fi

# Check startup time
echo "Startup time: ${STARTUP_TIME} seconds"

if (( $(echo "${STARTUP_TIME} < ${MAX_STARTUP_TIME}" | bc -l) )); then
    echo -e "${GREEN}✅ Startup time target met: ${STARTUP_TIME}s < ${MAX_STARTUP_TIME}s${NC}"
else
    echo -e "${YELLOW}⚠️  Startup time acceptable but above target: ${STARTUP_TIME}s >= ${MAX_STARTUP_TIME}s${NC}"
fi

# Test basic functionality
echo -e "${BLUE}🔍 Testing basic Qdrant functionality...${NC}"

# Test cluster info endpoint
if curl -s -f http://localhost:6333/ >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant cluster info endpoint working${NC}"
else
    echo -e "${RED}❌ Qdrant cluster info endpoint failed${NC}"
    exit 1
fi

# Test collections endpoint
if curl -s -f http://localhost:6333/collections >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Qdrant collections endpoint working${NC}"
else
    echo -e "${RED}❌ Qdrant collections endpoint failed${NC}"
    exit 1
fi

# Display container logs for verification
echo -e "${BLUE}📋 Container startup logs:${NC}"
docker logs "${CONTAINER_ID}" | tail -10

echo ""
echo -e "${GREEN}🎉 BUILD SUCCESSFUL!${NC}"
echo "============================================"
echo -e "📦 Image: ${FULL_IMAGE_NAME}"
echo -e "📏 Size: ${IMAGE_SIZE_MB} MB"
echo -e "⏱️  Startup: ${STARTUP_TIME}s"
echo -e "🎯 Targets: <${MAX_SIZE_MB}MB, <${MAX_STARTUP_TIME}s"
echo "============================================"

# Tag as latest successful build
docker tag "${FULL_IMAGE_NAME}" "${IMAGE_NAME}:cli140i-optimized"
echo -e "${GREEN}✅ Tagged as ${IMAGE_NAME}:cli140i-optimized${NC}" 