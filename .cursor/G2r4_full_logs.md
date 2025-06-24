# CI run 15841066262 – full raw logs

**Analysis Date:** June 24, 2025  
**Run ID:** 15841066262  
**Workflow:** CI Test Suite  
**Branch:** ci/final-519  
**Status:** Failed  
**Duration:** ~2 seconds (04:14:55Z to 04:15:02Z)

## Summary

The CI run failed immediately during the "Set up job" phase due to a **deprecated GitHub Actions version**.

**Root Cause:** The workflow uses `actions/upload-artifact: v3` which has been deprecated and automatically failed by GitHub.

## Run Metadata

| Field | Value |
|-------|-------|
| Run URL | https://github.com/Huyen1974/agent-data/actions/runs/15841066262 |
| Job Name | Test Suite (519 tests) |
| Job ID | 44653756318 |
| Conclusion | failure |
| Created At | 2025-06-24T04:14:55Z |
| Completed At | 2025-06-24T04:15:02Z |
| Runner | Ubuntu 24.04.2 LTS |
| Runner Version | 2.325.0 |

## Log Files

| File | Lines Kept | Source |
|------|------------|--------|
| 0_Test Suite (519 tests).txt | 24 (full) | GitHub Actions Log API |
| run_info_formatted.json | - | GitHub API (job metadata) |

## Full Log: 0_Test Suite (519 tests).txt

```log
2025-06-24T04:15:00.7956666Z Current runner version: '2.325.0'
2025-06-24T04:15:00.7981148Z ##[group]Operating System
2025-06-24T04:15:00.7982222Z Ubuntu
2025-06-24T04:15:00.7982722Z 24.04.2
2025-06-24T04:15:00.7983271Z LTS
2025-06-24T04:15:00.7983755Z ##[endgroup]
2025-06-24T04:15:00.7984240Z ##[group]Runner Image
2025-06-24T04:15:00.7984904Z Image: ubuntu-24.04
2025-06-24T04:15:00.7985424Z Version: 20250615.1.0
2025-06-24T04:15:00.7986448Z Included Software: https://github.com/actions/runner-images/blob/ubuntu24/20250615.1/images/ubuntu/Ubuntu2404-Readme.md
2025-06-24T04:15:00.7987862Z Image Release: https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20250615.1
2025-06-24T04:15:00.7988715Z ##[endgroup]
2025-06-24T04:15:00.7989225Z ##[group]Runner Image Provisioner
2025-06-24T04:15:00.7989858Z 2.0.437.1
2025-06-24T04:15:00.7990325Z ##[endgroup]
2025-06-24T04:15:00.7991257Z ##[group]GITHUB_TOKEN Permissions
2025-06-24T04:15:00.7993672Z Contents: read
2025-06-24T04:15:00.7994308Z Metadata: read
2025-06-24T04:15:00.7995002Z ##[endgroup]
2025-06-24T04:15:00.7997788Z Secret source: Actions
2025-06-24T04:15:00.7998478Z Prepare workflow directory
2025-06-24T04:15:00.8361769Z Prepare all required actions
2025-06-24T04:15:00.8399339Z Getting action download info
2025-06-24T04:15:01.1635818Z ##[error]This request has been automatically failed because it uses a deprecated version of `actions/upload-artifact: v3`. Learn more: https://github.blog/changelog/2024-04-16-deprecation-notice-v3-of-the-artifact-actions/
```

## Diagnostic Analysis

### Issue Description
The workflow failed because it uses `actions/upload-artifact@v3`, which GitHub deprecated and now automatically fails.

### Required Fix
Update the workflow YAML file to use `actions/upload-artifact@v4` instead of `actions/upload-artifact@v3`.

### Impact
- No tests were executed
- The failure occurred during job setup phase
- This affects all CI runs on the `ci/final-519` branch

### Next Steps
1. Update the workflow file(s) to use `actions/upload-artifact@v4`
2. Update any other deprecated actions if present
3. Re-run the CI pipeline

## File Manifest

Generated files in /tmp/ci_raw/:
- `0_Test Suite (519 tests).txt` (24 lines)
- `run_info.json` (raw job metadata)
- `run_info_formatted.json` (formatted job metadata)
- `run_logs.zip` (original logs archive)
- `G2r4_full_logs.md` (this report)

**Total log size:** < 1KB (very small due to early failure)
**Report generated:** June 24, 2025 