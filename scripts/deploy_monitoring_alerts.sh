#!/bin/bash

# Deploy monitoring alert policies for Agent Data system
# This script deploys alert policies for ingestion workflow failures

set -e

PROJECT_ID="chatgpt-db-project"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Deploying monitoring alert policies for Agent Data system..."
echo "Project: $PROJECT_ID"
echo "Root directory: $ROOT_DIR"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install gcloud CLI: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Error: Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Set the project
echo "📋 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Deploy ingestion workflow alert policy
echo "📊 Deploying ingestion workflow failure alert policy..."
if [ -f "$ROOT_DIR/alert_policy_ingestion_workflow.json" ]; then
    # Check if alert policy already exists
    EXISTING_POLICY=$(gcloud alpha monitoring policies list --filter="displayName:'Ingestion Workflow Failure Alert - Agent Data'" --format="value(name)" 2>/dev/null || true)

    if [ -n "$EXISTING_POLICY" ]; then
        echo "⚠️  Alert policy already exists: $EXISTING_POLICY"
        echo "🔄 Updating existing policy..."
        gcloud alpha monitoring policies update "$EXISTING_POLICY" \
            --policy-from-file="$ROOT_DIR/alert_policy_ingestion_workflow.json" \
            --quiet
        echo "✅ Updated ingestion workflow alert policy"
    else
        echo "🆕 Creating new alert policy..."
        gcloud alpha monitoring policies create \
            --policy-from-file="$ROOT_DIR/alert_policy_ingestion_workflow.json" \
            --quiet
        echo "✅ Created ingestion workflow alert policy"
    fi
else
    echo "❌ Error: alert_policy_ingestion_workflow.json not found"
    exit 1
fi

# Deploy Qdrant latency alert policy (optional)
echo "📊 Deploying Qdrant latency alert policy..."
if [ -f "$ROOT_DIR/alert_policy_qdrant_latency.json" ]; then
    EXISTING_QDRANT_POLICY=$(gcloud alpha monitoring policies list --filter="displayName:'Qdrant High Latency Alert'" --format="value(name)" 2>/dev/null || true)

    if [ -n "$EXISTING_QDRANT_POLICY" ]; then
        echo "⚠️  Qdrant alert policy already exists: $EXISTING_QDRANT_POLICY"
        echo "🔄 Updating existing policy..."
        gcloud alpha monitoring policies update "$EXISTING_QDRANT_POLICY" \
            --policy-from-file="$ROOT_DIR/alert_policy_qdrant_latency.json" \
            --quiet
        echo "✅ Updated Qdrant latency alert policy"
    else
        echo "🆕 Creating new Qdrant alert policy..."
        gcloud alpha monitoring policies create \
            --policy-from-file="$ROOT_DIR/alert_policy_qdrant_latency.json" \
            --quiet
        echo "✅ Created Qdrant latency alert policy"
    fi
else
    echo "⚠️  Warning: alert_policy_qdrant_latency.json not found, skipping"
fi

# List deployed policies
echo ""
echo "📋 Current alert policies:"
gcloud alpha monitoring policies list \
    --filter="displayName:('Ingestion Workflow' OR 'Qdrant')" \
    --format="table(displayName,enabled,conditions.len():label=CONDITIONS)"

echo ""
echo "✅ Monitoring alert deployment completed!"
echo ""
echo "📝 Next steps:"
echo "1. Configure notification channels (email, Slack, etc.)"
echo "2. Test alert policies with simulated failures"
echo "3. Monitor alert policy performance in Cloud Monitoring console"
echo ""
echo "🔗 Cloud Monitoring Console:"
echo "https://console.cloud.google.com/monitoring/alerting/policies?project=$PROJECT_ID"
