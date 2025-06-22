#!/bin/bash

# Deploy Qdrant Latency Probe Cloud Function
# CLI121: Deploy latency monitoring for rate-limit risk reduction

set -e

# Configuration
PROJECT_ID="chatgpt-db-project"
REGION="asia-southeast1"
FUNCTION_NAME="qdrant-latency-probe"
SERVICE_ACCOUNT="gemini-service-account@chatgpt-db-project.iam.gserviceaccount.com"
RUNTIME="python310"
ENTRY_POINT="latency_probe_function"
MEMORY="512Mi"
TIMEOUT="60s"
MIN_INSTANCES="0"
MAX_INSTANCES="1"

echo "🚀 Deploying Qdrant Latency Probe Cloud Function"
echo "=================================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Function: $FUNCTION_NAME"
echo "Service Account: $SERVICE_ACCOUNT"
echo ""

# Check if we're in the right directory
if [ ! -f "src/agent_data_manager/utils/latency_probe_function.py" ]; then
    echo "❌ Error: latency_probe_function.py not found"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Create a temporary directory for deployment
TEMP_DIR=$(mktemp -d)
echo "📁 Creating deployment package in: $TEMP_DIR"

# Copy necessary files
cp -r src/agent_data_manager "$TEMP_DIR/"
cp pyproject.toml "$TEMP_DIR/"
cp requirements.txt "$TEMP_DIR/"

# Create main.py for Cloud Function entry point
cat > "$TEMP_DIR/main.py" << 'EOF'
"""Cloud Function entry point for Qdrant latency probe."""

import asyncio
import logging
from agent_data_manager.utils.latency_probe_function import latency_probe_function

# Configure logging
logging.basicConfig(level=logging.INFO)

def main(request):
    """HTTP Cloud Function entry point."""
    return asyncio.run(latency_probe_function(request))

if __name__ == "__main__":
    # For local testing
    asyncio.run(latency_probe_function())
EOF

# Create requirements.txt for Cloud Function
cat > "$TEMP_DIR/requirements.txt" << 'EOF'
qdrant-client>=1.7.0
google-cloud-secret-manager>=2.16.0
google-cloud-firestore>=2.11.0
fastapi>=0.104.0
openai>=1.3.0
python-multipart>=0.0.6
passlib[bcrypt]>=1.7.4
python-jose[cryptography]>=3.3.0
firebase-admin>=6.2.0
google-cloud-storage>=2.10.0
google-cloud-monitoring>=2.15.0
prometheus-client>=0.17.0
asyncio
logging
datetime
time
typing
EOF

echo "📦 Deploying Cloud Function..."

# Deploy the Cloud Function
gcloud functions deploy "$FUNCTION_NAME" \
    --gen2 \
    --runtime="$RUNTIME" \
    --region="$REGION" \
    --source="$TEMP_DIR" \
    --entry-point="main" \
    --trigger-http \
    --allow-unauthenticated \
    --service-account="$SERVICE_ACCOUNT" \
    --memory="$MEMORY" \
    --timeout="$TIMEOUT" \
    --min-instances="$MIN_INSTANCES" \
    --max-instances="$MAX_INSTANCES" \
    --set-env-vars="QDRANT_API_KEY=\$(gcloud secrets versions access latest --secret=qdrant-api-key-sg --project=$PROJECT_ID),QDRANT_URL=https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io,QDRANT_COLLECTION_NAME=agent_data_vectors,VECTOR_DIMENSION=1536" \
    --project="$PROJECT_ID"

if [ $? -eq 0 ]; then
    echo "✅ Cloud Function deployed successfully!"

    # Get the function URL
    FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(serviceConfig.uri)")
    echo "🌐 Function URL: $FUNCTION_URL"

    echo ""
    echo "🕐 Setting up Cloud Scheduler for hourly execution..."

    # Create Cloud Scheduler job for hourly execution
    JOB_NAME="qdrant-latency-probe-hourly"

    # Check if job already exists
    if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
        echo "⚠️  Scheduler job already exists, updating..."
        gcloud scheduler jobs update http "$JOB_NAME" \
            --location="$REGION" \
            --schedule="0 * * * *" \
            --uri="$FUNCTION_URL" \
            --http-method="POST" \
            --headers="Content-Type=application/json" \
            --message-body='{"trigger":"hourly"}' \
            --project="$PROJECT_ID"
    else
        echo "📅 Creating new scheduler job..."
        gcloud scheduler jobs create http "$JOB_NAME" \
            --location="$REGION" \
            --schedule="0 * * * *" \
            --uri="$FUNCTION_URL" \
            --http-method="POST" \
            --headers="Content-Type=application/json" \
            --message-body='{"trigger":"hourly"}' \
            --project="$PROJECT_ID"
    fi

    if [ $? -eq 0 ]; then
        echo "✅ Cloud Scheduler job configured for hourly execution"
        echo "📋 Job details:"
        gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" --project="$PROJECT_ID" --format="table(name,schedule,state)"
    else
        echo "⚠️  Warning: Cloud Scheduler job creation failed, but function is deployed"
    fi

    echo ""
    echo "🎯 Testing function..."
    curl -X POST "$FUNCTION_URL" -H "Content-Type: application/json" -d '{"test":true}' || echo "⚠️  Function test may have failed"

else
    echo "❌ Cloud Function deployment failed"
    exit 1
fi

# Clean up temporary directory
rm -rf "$TEMP_DIR"
echo "🧹 Cleaned up temporary files"

echo ""
echo "🎉 Deployment Summary:"
echo "======================"
echo "✅ Function: $FUNCTION_NAME deployed to $REGION"
echo "✅ Service Account: $SERVICE_ACCOUNT"
echo "✅ Scheduler: Hourly execution configured"
echo "✅ Monitoring: Ready to log latency to logs/latency.log"
echo ""
echo "📝 Next steps:"
echo "1. Monitor function logs: gcloud functions logs read $FUNCTION_NAME --region=$REGION"
echo "2. Check scheduler: gcloud scheduler jobs list --location=$REGION"
echo "3. View latency logs: check logs/latency.log file"
echo "4. Set up Cloud Monitoring alerts using alert_policy_qdrant_latency.json"
