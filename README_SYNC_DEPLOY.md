# Sync Secrets and Deploy Script

## Overview
This script (`sync_secrets_and_deploy.sh`) automates the process of:
1. Copying GitHub secrets from a source repository to `Huyen1974/agent-data`
2. Triggering the "Deploy Containers" workflow
3. Watching the deployment until completion

## Prerequisites
- GitHub CLI (`gh`) installed and authenticated
- Access to both source and destination repositories
- The source repository must have the required secrets configured

## Required Secrets
The script copies these 3 secrets:
- `PROJECT_ID` - GCP Project ID
- `GCP_SERVICE_ACCOUNT` - GCP Service Account JSON
- `GCP_WORKLOAD_IDENTITY_PROVIDER` - GCP Workload Identity Provider

## Usage

### 1. Edit the Source Repository
Open `sync_secrets_and_deploy.sh` and replace `<OWNER/REPO-MẪU>` with your source repository:

```bash
# Change this line:
SRC="<OWNER/REPO-MẪU>"

# To something like:
SRC="myusername/working-repo"
```

### 2. Run the Script
```bash
./sync_secrets_and_deploy.sh
```

### 3. Monitor Output
The script will:
- ✅ Validate the source repository is set
- 🔑 Copy each secret with progress feedback
- 🚀 Trigger the CI workflow
- 👀 Watch the workflow run until completion
- 🎉 Report success or failure

## Error Handling
- Script stops on first error (`set -e`)
- Validates source repo is configured
- Checks each secret exists before copying
- Returns non-zero exit code on CI failure

## Example Output
```
🔑  Copy 3 secrets từ myuser/source-repo → Huyen1974/agent-data …
  Copying secret: PROJECT_ID
    ✅  PROJECT_ID copied successfully
  Copying secret: GCP_SERVICE_ACCOUNT
    ✅  GCP_SERVICE_ACCOUNT copied successfully
  Copying secret: GCP_WORKLOAD_IDENTITY_PROVIDER
    ✅  GCP_WORKLOAD_IDENTITY_PROVIDER copied successfully
✅  Secrets đã đồng bộ.
🚀  Trigger CI …
👀  Watching workflow run …
🎉  Deployment complete!
```

## Troubleshooting
- Ensure GitHub CLI is authenticated: `gh auth status`
- Verify access to both repositories: `gh repo view <repo>`
- Check secrets exist in source repo: `gh secret list --repo <source-repo>` 