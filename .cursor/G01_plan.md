# G01 GitHub Repository Setup Plan

**Date:** June 22, 2025, 17:00 +07  
**Repository:** `Huyen1974/agent-data`  
**Objective:** Create dedicated GitHub repository for Agent Data project with CI/CD setup

## Execution Summary

### ✅ Completed Steps

1. **Repository Creation**
   - Created GitHub repository `Huyen1974/agent-data` as public repository
   - Repository URL: https://github.com/Huyen1974/agent-data
   - Added comprehensive description about Agent Data project

2. **Local Repository Setup**
   - Navigated to `/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data`
   - Found existing git repository on branch `stabilize/lock`
   - Added remote origin: `https://github.com/Huyen1974/agent-data.git`
   - Switched to main branch for initial commit

3. **Documentation Creation**
   - Created comprehensive README.md with project overview, architecture, and setup instructions
   - Created .env.sample with frozen environment variables for configuration
   - Created this plan document (.cursor/G01_plan.md)

4. **CI Permissions Setup**
   - Updated production Workload Identity Provider to include `repo:Huyen1974/agent-data`
   - Updated test Workload Identity Provider to include `repo:Huyen1974/agent-data`
   - Created GitHub Actions workflow for authentication testing

### 🔄 Next Steps (To be completed)

5. **Initial Commit and Push**
   - Stage and commit README.md, .env.sample, and workflow files
   - Push to main branch
   - Tag with `v0.1-green-repo-init`

6. **GitHub Secrets Setup**
   - Add required secrets via GitHub UI:
     - GCP_WORKLOAD_IDENTITY_PROVIDER
     - GCP_SERVICE_ACCOUNT
     - PROJECT_ID

7. **CI Verification**
   - Run authentication test workflow
   - Verify Workload Identity Federation works correctly

## Technical Details

### Repository Structure
- **Location:** `/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data`
- **Remote:** `https://github.com/Huyen1974/agent-data.git`
- **Current Branch:** `main`
- **Workload Identity:** Updated for both production and test environments

### Workload Identity Configuration
- **Production Provider:** `projects/812872501910/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- **Test Provider:** `projects/1042559846495/locations/global/workloadIdentityPools/github-test-pool/providers/github-test-provider`
- **Condition:** `assertion.repository=='Huyen1974/chatgpt-githubnew' || assertion.repository=='Huyen1974/agent-data'`

### Required GitHub Secrets
- `GCP_WORKLOAD_IDENTITY_PROVIDER`: `projects/812872501910/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- `GCP_SERVICE_ACCOUNT`: `chatgpt-deployer@github-chatgpt-ggcloud.iam.gserviceaccount.com`
- `PROJECT_ID`: `github-chatgpt-ggcloud`

## Commands Executed

```bash
# Repository creation
gh repo create Huyen1974/agent-data --public --description "..." --clone=false

# Local setup
cd ADK/agent_data
git remote add origin https://github.com/Huyen1974/agent-data.git
git checkout main

# Workload Identity updates
gcloud iam workload-identity-pools providers update-oidc github-provider \
  --location=global --workload-identity-pool=github-pool \
  --project=github-chatgpt-ggcloud \
  --attribute-condition="assertion.repository=='Huyen1974/chatgpt-githubnew' || assertion.repository=='Huyen1974/agent-data'"

gcloud iam workload-identity-pools providers update-oidc github-test-provider \
  --location=global --workload-identity-pool=github-test-pool \
  --project=chatgpt-db-project \
  --attribute-condition="assertion.repository=='Huyen1974/chatgpt-githubnew' || assertion.repository=='Huyen1974/agent-data'"
```

## Verification Status

### ✅ Completed
- Repository exists and is accessible
- Workload Identity Providers updated successfully
- Local repository configured with remote origin
- Documentation and workflow files created

### ⏳ Pending
- Initial commit and push to main branch
- GitHub secrets configuration via UI
- Authentication workflow testing
- Tag creation for milestone

## Next Actions Required

1. **Manual GitHub Secrets Setup** (via GitHub UI):
   - Navigate to https://github.com/Huyen1974/agent-data/settings/secrets/actions
   - Add the required secrets listed above

2. **Complete Initial Commit**:
   ```bash
   git add README.md .env.sample .cursor/G01_plan.md .github/workflows/auth-test.yaml
   git commit -m "Initial repository setup with documentation and CI configuration"
   git push origin main
   git tag v0.1-green-repo-init
   git push origin v0.1-green-repo-init
   ```

3. **Test CI Authentication**:
   - Trigger the auth-test workflow manually
   - Verify successful authentication to GCP

## Risk Assessment

### ✅ Mitigated
- Workload Identity Provider conflicts (both environments updated)
- Repository creation and configuration
- MacBook M1 resource constraints (no heavy operations)

### ⚠️ Remaining
- GitHub secrets need manual configuration
- Authentication workflow needs testing
- Branch strategy may need adjustment based on existing codebase

## Success Criteria

- ✅ Repository created and accessible
- ✅ Workload Identity Providers configured
- ⏳ Initial commit pushed successfully
- ⏳ GitHub secrets configured
- ⏳ Authentication workflow passes
- ⏳ Tag `v0.1-green-repo-init` created

## Notes

- GitHub CLI has some display issues but core functionality works
- Workload Identity Provider updates were successful
- Local repository already contains substantial Agent Data codebase
- No timeouts or hanging commands encountered
- Ready for manual secrets configuration and final push
