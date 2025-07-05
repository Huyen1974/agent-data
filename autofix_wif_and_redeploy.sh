#!/bin/bash

# Prompt D12-autofix-wif-and-redeploy   (auto-execute, stop-on-error)

# ---------- EDIT IF NEEDED ----------
PROJECT_ID="chatgpt-db-project"                     # Test project
SA_EMAIL="chatgpt-deployer@chatgpt-db-project.iam.gserviceaccount.com"
POOL_ID="github-test-pool"
PROVIDER_ID="github-test-provider"
REPO_OWNER="Huyen1974"
REPO_NAME="agent-data"
LOCATION="global"
# ---------- DO NOT EDIT BELOW ----------

set -euo pipefail
REPO="${REPO_OWNER}/${REPO_NAME}"

echo "📋  Deriving project number …"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

###############################################################################
# 1. Workload-Identity Pool & Provider
###############################################################################
if ! gcloud iam workload-identity-pools describe "$POOL_ID" \
        --location="$LOCATION" --project="$PROJECT_ID" &>/dev/null; then
  echo "🆕  Creating Workload Identity Pool $POOL_ID"
  gcloud iam workload-identity-pools create "$POOL_ID" \
        --location="$LOCATION" \
        --project="$PROJECT_ID" \
        --display-name="GitHub Actions Pool"
else
  echo "✔️   Pool $POOL_ID already exists"
fi

if ! gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
        --workload-identity-pool="$POOL_ID" \
        --location="$LOCATION" --project="$PROJECT_ID" &>/dev/null; then
  echo "🆕  Creating Provider $PROVIDER_ID (repo-scoped)"
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
        --workload-identity-pool="$POOL_ID" --location="$LOCATION" \
        --project="$PROJECT_ID" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
        --attribute-condition="attribute.repository=='$REPO'"
else
  echo "✔️   Provider $PROVIDER_ID already exists"
fi

###############################################################################
# 2. IAM bindings (idempotent)
###############################################################################
PRINCIPAL="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/${LOCATION}/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

echo "🔐  Ensuring roles on $SA_EMAIL …"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
      --project="$PROJECT_ID" --quiet \
      --role="roles/iam.workloadIdentityUser" --member="$PRINCIPAL" || true

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
      --project="$PROJECT_ID" --quiet \
      --role="roles/iam.serviceAccountTokenCreator" --member="serviceAccount:${SA_EMAIL}" || true

gcloud projects add-iam-policy-binding "$PROJECT_ID" --quiet \
      --member="serviceAccount:${SA_EMAIL}" --role="roles/artifactregistry.writer" || true

echo "✅  IAM roles ensured."

###############################################################################
# 3. Sync secret (if provider path changed)
###############################################################################
PROVIDER_PATH="projects/${PROJECT_NUMBER}/locations/${LOCATION}/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
CURRENT_SECRET=$(gh secret list --repo "$REPO" | grep "GCP_WORKLOAD_ID_PROVIDER" | awk '{print $1}' || echo "")
if [[ -z "$CURRENT_SECRET" ]] || [[ "$CURRENT_SECRET" != "GCP_WORKLOAD_ID_PROVIDER" ]]; then
  echo "🔄  Setting secret GCP_WORKLOAD_ID_PROVIDER → $PROVIDER_PATH"
  echo "$PROVIDER_PATH" | gh secret set GCP_WORKLOAD_ID_PROVIDER --repo "$REPO"
else
  echo "✔️   Secret already exists"
fi

###############################################################################
# 4. Trigger workflow & watch
###############################################################################
echo "🚀  Triggering workflow Deploy Containers …"
gh workflow run "Deploy Containers" --ref main --repo "$REPO"

echo "⏳  Waiting for latest run to finish (may take ~5-7 min) …"
sleep 5  # Give GitHub a moment to register the new run
LATEST_RUN_ID=$(gh run list --repo "$REPO" --workflow "Deploy Containers" --limit 1 --json databaseId --jq '.[0].databaseId')
if [[ -n "$LATEST_RUN_ID" ]]; then
  gh run watch "$LATEST_RUN_ID" --repo "$REPO" --exit-status
  echo "🏁  Workflow finished – see status above."
else
  echo "⚠️  Could not find run ID to watch. Check manually with: gh run list --repo $REPO"
fi
