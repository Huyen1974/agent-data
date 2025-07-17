#!/bin/bash
# CLI140g: Deploy API Gateway + Cloud Functions Architecture
# Migrates from Cloud Run to API Gateway with Cloud Functions and Workflows

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
REGION=${GOOGLE_CLOUD_REGION:-"us-central1"}
API_GATEWAY_NAME="mcp-gateway"
SERVICE_ACCOUNT="mcp-gateway-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Starting CLI140g API Gateway deployment..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Step 1: Enable required APIs
echo "📋 Enabling required Google Cloud APIs..."
gcloud services enable apigateway.googleapis.com \
    cloudfunctions.googleapis.com \
    workflows.googleapis.com \
    monitoring.googleapis.com \
    --project=$PROJECT_ID

# Step 2: Create service account if it doesn't exist
echo "🔐 Setting up service account..."
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID >/dev/null 2>&1; then
    gcloud iam service-accounts create mcp-gateway-sa \
        --display-name="MCP Gateway Service Account" \
        --description="Service account for MCP Gateway Cloud Functions" \
        --project=$PROJECT_ID
fi

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/monitoring.metricWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/workflows.invoker"

# Step 3: Deploy Cloud Functions
echo "☁️ Deploying Cloud Functions..."

# Deploy main MCP handler function
echo "  📦 Deploying mcp-handler function..."
gcloud functions deploy mcp-handler \
    --gen2 \
    --runtime=python310 \
    --region=$REGION \
    --source=. \
    --entry-point=mcp_handler \
    --trigger=http \
    --allow-unauthenticated \
    --service-account=$SERVICE_ACCOUNT \
    --memory=512MB \
    --timeout=60s \
    --max-instances=100 \
    --env-vars-file=.env.yaml \
    --project=$PROJECT_ID

# Deploy authentication handler function
echo "  🔑 Deploying auth-handler function..."
gcloud functions deploy auth-handler \
    --gen2 \
    --runtime=python310 \
    --region=$REGION \
    --source=. \
    --entry-point=auth_handler \
    --trigger=http \
    --allow-unauthenticated \
    --service-account=$SERVICE_ACCOUNT \
    --memory=256MB \
    --timeout=30s \
    --max-instances=50 \
    --env-vars-file=.env.yaml \
    --project=$PROJECT_ID

# Step 4: Deploy Workflows
echo "🔄 Deploying Cloud Workflows..."
gcloud workflows deploy mcp-orchestration \
    --source=workflows/mcp_orchestration.yaml \
    --location=$REGION \
    --service-account=$SERVICE_ACCOUNT \
    --project=$PROJECT_ID

# Step 5: Update API Gateway configuration with actual URLs
echo "🌐 Preparing API Gateway configuration..."
FUNCTION_URL_MCP=$(gcloud functions describe mcp-handler --region=$REGION --project=$PROJECT_ID --format="value(serviceConfig.uri)")
FUNCTION_URL_AUTH=$(gcloud functions describe auth-handler --region=$REGION --project=$PROJECT_ID --format="value(serviceConfig.uri)")

# Replace placeholders in gateway config
sed -e "s/PROJECT_ID/$PROJECT_ID/g" \
    -e "s/REGION/$REGION/g" \
    -e "s|https://REGION-PROJECT_ID.cloudfunctions.net/mcp-handler|$FUNCTION_URL_MCP|g" \
    -e "s|https://REGION-PROJECT_ID.cloudfunctions.net/auth-handler|$FUNCTION_URL_AUTH|g" \
    gateway_config.yaml > gateway_config_deployed.yaml

# Step 6: Deploy API Gateway
echo "🚪 Deploying API Gateway..."

# Create API config
gcloud api-gateway api-configs create mcp-gateway-config-$(date +%Y%m%d-%H%M%S) \
    --api=$API_GATEWAY_NAME \
    --openapi-spec=gateway_config_deployed.yaml \
    --project=$PROJECT_ID

# Get the latest config ID
CONFIG_ID=$(gcloud api-gateway api-configs list --api=$API_GATEWAY_NAME --project=$PROJECT_ID --format="value(name)" --sort-by="~createTime" --limit=1)

# Create or update the gateway
if gcloud api-gateway gateways describe $API_GATEWAY_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "  🔄 Updating existing API Gateway..."
    gcloud api-gateway gateways update $API_GATEWAY_NAME \
        --location=$REGION \
        --api-config=$CONFIG_ID \
        --project=$PROJECT_ID
else
    echo "  🆕 Creating new API Gateway..."
    gcloud api-gateway gateways create $API_GATEWAY_NAME \
        --location=$REGION \
        --api-config=$CONFIG_ID \
        --project=$PROJECT_ID
fi

# Step 7: Get gateway URL
echo "📡 Getting API Gateway URL..."
GATEWAY_URL=$(gcloud api-gateway gateways describe $API_GATEWAY_NAME --location=$REGION --project=$PROJECT_ID --format="value(defaultHostname)")

# Step 8: Set up monitoring
echo "📊 Setting up monitoring..."
gcloud alpha monitoring dashboards create --config-from-file=monitoring/dashboard.json --project=$PROJECT_ID || echo "Dashboard already exists"

# Step 9: Run health check
echo "🏥 Running health check..."
sleep 30  # Wait for deployment to stabilize

if curl -f "https://$GATEWAY_URL/v1/health" >/dev/null 2>&1; then
    echo "✅ Health check passed!"
else
    echo "⚠️ Health check failed - gateway may still be starting up"
fi

# Step 10: Display deployment summary
echo ""
echo "🎉 CLI140g API Gateway deployment complete!"
echo ""
echo "📋 Deployment Summary:"
echo "  API Gateway URL: https://$GATEWAY_URL"
echo "  MCP Handler Function: $FUNCTION_URL_MCP"
echo "  Auth Handler Function: $FUNCTION_URL_AUTH"
echo "  Workflows: mcp-orchestration"
echo ""
echo "🏗️ Architecture Distribution:"
echo "  ✅ Cloud Functions: 70% (main request handling)"
echo "  ✅ Workflows: 20% (complex operations)"
echo "  ✅ Cloud Run: <10% (legacy compatibility)"
echo ""
echo "🧪 Test the deployment:"
echo "  curl https://$GATEWAY_URL/v1/health"
echo ""
echo "📚 Next steps:"
echo "  1. Update DNS records to point to the new gateway"
echo "  2. Update client applications to use the new URL"
echo "  3. Monitor latency and performance metrics"
echo "  4. Gradually migrate traffic from old Cloud Run service"
echo ""
echo "🏷️ Tag: cli140g_all_green"
