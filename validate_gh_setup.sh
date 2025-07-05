#!/bin/bash

# Validation script for GitHub CLI setup and repository access
# Run this before using sync_secrets_and_deploy.sh

echo "🔍  Validating GitHub CLI setup..."

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌  GitHub CLI (gh) is not installed"
    echo "    Install it from: https://cli.github.com/"
    exit 1
fi

echo "✅  GitHub CLI is installed"

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌  GitHub CLI is not authenticated"
    echo "    Run: gh auth login"
    exit 1
fi

echo "✅  GitHub CLI is authenticated"

# Check access to destination repository
DST="Huyen1974/agent-data"
if ! gh repo view "$DST" &> /dev/null; then
    echo "❌  Cannot access destination repository: $DST"
    echo "    Make sure you have access to this repository"
    exit 1
fi

echo "✅  Can access destination repository: $DST"

# Prompt for source repository validation
echo ""
echo "📝  Please provide your source repository (the one with working CI):"
read -p "    Repository (format: owner/repo): " SOURCE_REPO

if [[ -z "$SOURCE_REPO" ]]; then
    echo "❌  No source repository provided"
    exit 1
fi

# Check access to source repository
if ! gh repo view "$SOURCE_REPO" &> /dev/null; then
    echo "❌  Cannot access source repository: $SOURCE_REPO"
    echo "    Make sure the repository exists and you have access"
    exit 1
fi

echo "✅  Can access source repository: $SOURCE_REPO"

# Check if required secrets exist in source repo
echo ""
echo "🔑  Checking required secrets in source repository..."

MISSING_SECRETS=()
for SECRET in PROJECT_ID GCP_SERVICE_ACCOUNT GCP_WORKLOAD_IDENTITY_PROVIDER; do
    if ! gh secret view "$SECRET" --repo "$SOURCE_REPO" &> /dev/null; then
        MISSING_SECRETS+=("$SECRET")
    else
        echo "✅  Secret found: $SECRET"
    fi
done

if [[ ${#MISSING_SECRETS[@]} -gt 0 ]]; then
    echo "❌  Missing secrets in $SOURCE_REPO:"
    for SECRET in "${MISSING_SECRETS[@]}"; do
        echo "    - $SECRET"
    done
    echo "    Please configure these secrets in the source repository"
    exit 1
fi

echo ""
echo "🎉  All validations passed!"
echo ""
echo "📋  Next steps:"
echo "1. Edit sync_secrets_and_deploy.sh"
echo "2. Replace SRC=\"<OWNER/REPO-MẪU>\" with SRC=\"$SOURCE_REPO\""
echo "3. Run: ./sync_secrets_and_deploy.sh" 