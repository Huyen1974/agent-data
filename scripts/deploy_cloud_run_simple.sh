#!/bin/bash
# Simplified Cloud Run Deployment Script for Qdrant
#
# This script deploys a pre-built Qdrant image to Cloud Run with environment variables
# for hybrid sync switching between Qdrant Cloud and local Docker mode.

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"qdrant-agent"}
QDRANT_COLLECTION_NAME=${QDRANT_COLLECTION_NAME:-"my_collection"}
GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"qdrant-snapshots"}

echo "=== Simplified Cloud Run Deployment for Qdrant ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo "Collection: ${QDRANT_COLLECTION_NAME}"
echo "GCS Bucket: ${GCS_BUCKET_NAME}"
echo ""

# Check if gcloud is authenticated
echo "Checking gcloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "Error: No active gcloud authentication found."
    echo "Please run: gcloud auth login"
    exit 1
fi

# Set the project
echo "Setting gcloud project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Deploy to Cloud Run using official Qdrant image
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image qdrant/qdrant:v1.7.4 \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 10 \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --port 6333 \
    --set-env-vars "QDRANT_URL=https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io" \
    --set-env-vars "QDRANT_COLLECTION_NAME=${QDRANT_COLLECTION_NAME}" \
    --set-env-vars "GCS_BUCKET_NAME=${GCS_BUCKET_NAME}" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "MODE=cloud"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: ${SERVICE_URL}"
echo "Health Check: ${SERVICE_URL}/health"
echo ""
echo "To test the deployment:"
echo "curl ${SERVICE_URL}/health"
echo ""
echo "To view logs:"
echo "gcloud logs tail --follow --service=${SERVICE_NAME}"
echo ""
echo "To delete the service:"
echo "gcloud run services delete ${SERVICE_NAME} --region=${REGION}"
echo ""
echo "Note: This deployment starts in 'cloud' mode pointing to Qdrant Cloud."
echo "The Cloud Scheduler will switch between 'cloud' and 'docker' modes."
