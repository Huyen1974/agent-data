# CLI140m.71 Plan: Replicate Repository Setup and Manage Buckets with Terraform

**Date:** July 3, 2025, 16:30 +07

## Context

- **Repository:** Huyen1974/agent-data contains Agent Data code, 157 unit tests (tests/), Dockerfile, requirements.txt, pytest.ini, .env.sample
- **Docker Image:** ghcr.io/huyen1974/agent-data:v0.1.29B (multi-platform, Python 3.10.17, ~550MB MacBook, 1.75GB PC)
- **Buckets:** huyen1974-faiss-index-storage-test, qdrant-snapshots, possibly unmanaged by Terraform
- **Status:** CLI140m.69 achieved 519 tests (0 Failed, 8 Skipped), but collect-only unstable

## Issues

- Missing containers/ directory for deploy_containers.yaml
- WIF auth errors (secret name mismatch)
- Unmanaged buckets in Terraform
- CI not green
- Old tag v0.1.25C on GHCR

## Goals

1. Replicate Huyen1974/chatgpt-githubnew setup: containers/, workflows, secrets
2. Manage buckets via Terraform: Import existing buckets, create state bucket
3. Ensure CI green: Fix directory, auth, run test_fast (157 tests), tag v0.2-ci-green
4. Add test to verify bucket existence
5. Commit .env.sample, load in test fixtures

## Execution Steps

### Step 1: Clone Repository Structure ✅
- Clone Huyen1974/chatgpt-githubnew to /tmp/template_repo
- Copy containers/ to ADK/agent_data/containers/
- Move Dockerfile to containers/agent-data/Dockerfile
- **Verification:** `ls -l ADK/agent_data/containers/agent-data/Dockerfile`

### Step 2: Sync Workflows
- Copy .github/workflows/{ci.yml,deploy_containers.yaml} from template
- Update deploy_containers.yaml to reference containers/agent-data/Dockerfile
- Fix secret: Replace GCP_WORKLOAD_ID_PROVIDER with GCP_WORKLOAD_IDENTITY_PROVIDER

### Step 3: Sync Secrets
- List secrets: `gh secret list --repo Huyen1974/chatgpt-githubnew`
- Copy secrets to Huyen1974/agent-data
- **Verification:** `gh secret list --repo Huyen1974/agent-data`

### Step 4: Configure Terraform
- Create terraform/main.tf with bucket resources
- Create state bucket: `gcloud storage buckets create gs://huyen1974-agent-data-terraform-state`
- Run: `terraform init`, `terraform import`, `terraform apply`

### Step 5: Add Test
- Create tests/test_terraform_buckets.py to verify bucket existence
- Run: `pytest -m "unit and not slow" --qdrant-mock --timeout=8`

### Step 6: Run CI and Tag
- Trigger: `gh workflow run ci.yml --ref main --repo Huyen1974/agent-data`
- Monitor: Check https://github.com/Huyen1974/agent_data/actions
- Tag: `git tag v0.2-ci-green && git push origin v0.2-ci-green`

### Step 7: Clean GHCR
- Delete v0.1.25C: `gh api -X DELETE /repos/Huyen1974/agent-data/packages/container/agent-data/versions/<version_id>`
- **Verification:** `gh api /repos/Huyen1974/agent-data/packages/container/agent-data/versions`

## Expected Results

- Directory: containers/agent-data/Dockerfile exists
- Workflows: ci.yml, deploy_containers.yaml copied, secrets fixed
- Secrets: 6 secrets present in Huyen1974/agent-data
- Terraform: Buckets imported, terraform apply succeeds, test passes
- CI: test_fast green (157/157 tests), image pushed
- GHCR: Only v0.1.29B, latest remain
- Git: Commit completed, .env.sample updated, v0.2-ci-green tagged

## Notes

- **Confidence:** Verify >90% before executing
- **Auto-execution:** Proceed until complete
- **Incremental:** Fix one issue, verify, proceed
- **M1:** Use --qdrant-mock, --timeout=8, sleep 0.5s, cleanup caches
- **Git:** Run full suite before writes, commit .env.sample, add one test
- **Risks:** Backup Terraform state to G:\My Drive\Cursor_backup, verify WIF, use same secrets
- **Storage:** All in /Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data 