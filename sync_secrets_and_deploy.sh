#!/bin/bash

# SYNC-SECRETS-AND-RERUN-CI (auto, stop-on-error)
# Script to copy GitHub secrets from source repo and trigger CI deployment

set -e  # Exit on any error

# --------- EDIT THIS LINE ONLY ---------
SRC="TEMPLATE_OWNER/TEMPLATE_REPO"   # put the green repo here
# --------------------------------------

DST="Huyen1974/agent-data"
WF="Deploy Containers"

echo "Copying secrets from $SRC to $DST …"
for S in PROJECT_ID GCP_SERVICE_ACCOUNT GCP_WORKLOAD_IDENTITY_PROVIDER; do
  VAL=$(gh secret view "$S" --repo "$SRC" --json value -q .value 2>/dev/null)
  if [ -z "$VAL" ]; then
    echo "Secret $S is missing in $SRC – aborting."; exit 1
  fi
  printf '%s' "$VAL" | gh secret set "$S" --repo "$DST" --body -
done
echo "Secrets synced."

echo "Triggering CI …"
gh workflow run "$WF" --repo "$DST" --ref main
gh run watch --repo "$DST" --workflow "$WF" --exit-status   # 0 = CI green 