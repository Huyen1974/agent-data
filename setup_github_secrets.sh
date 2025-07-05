#!/bin/bash

# ---------- EDIT THESE VALUES ----------
PROJECT_ID_VALUE="github-chatgpt-ggcloud"
PROJECT_ID_TEST_VALUE="chatgpt-db-project"
PROVIDER_PROD="projects/812872501910/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
PROVIDER_TEST="projects/1042559846495/locations/global/workloadIdentityPools/github-test-pool/providers/github-test-provider"
# ---------------------------------------

REPO="Huyen1974/agent-data"
WF="Deploy Containers"

echo "Setting missing secrets …"
printf '%s' "$PROJECT_ID_VALUE"  | gh secret set PROJECT_ID  --repo "$REPO" --body -
printf '%s' "$PROJECT_ID_TEST_VALUE"  | gh secret set PROJECT_ID_TEST  --repo "$REPO" --body -
printf '%s' "$PROVIDER_PROD"  | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$REPO" --body -
printf '%s' "$PROVIDER_TEST"  | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER_TEST --repo "$REPO" --body -

echo "Secret list after update:"
gh secret list --repo "$REPO"

echo "Triggering CI …"
gh workflow run "$WF" --repo "$REPO" --ref main
gh run watch --repo "$REPO" --workflow "$WF" --exit-status   # 0 = CI green 