# CLI143 Execution Plan
**Date:** July 3, 2025, 18:25 +07  
**Repository:** Huyen1974/agent-data  
**Target:** Complete CLI142 goals to achieve green CI with 2 tests, tag v0.3-ci-light-green

## Current Situation Analysis
- **CI Status:** Green on run 6e2cbed, ci/106-final-green branch
- **Docker Image:** ghcr.io/huyen1974/agent-data:v0.1.29B (Python 3.10.17)
- **Test Suite:** ~496 tests total, ~106 unit tests (pytest -m "unit and not slow")
- **Target Tests:** 2 specific tests for lightweight CI
- **Issue:** CLI142 failed at tagging due to dquote error

## Issues Identified

### 1. Dquote Error
**Status:** Investigating  
**Location:** Likely in .github/workflows/ci.yml Python script  
**Analysis:** Current heredoc syntax `<<'PY'` appears correct, need to check CI logs

### 2. Manifest Filtering  
**Status:** Confirmed  
**File:** tests/manifest_106.txt exists with 106 test entries  
**Solution:** Remove the manifest file completely  

### 3. Repo Diff Incomplete
**Status:** Pending  
**Required:** Compare agent-data vs chatgpt-githubnew repositories

### 4. Test Count Verification
**Status:** Need verification  
**Target:** Confirm "unit and not slow" yields expected count

## Execution Steps

### Step 1: Fix Dquote Error
- Check CI logs for specific error details
- Review ci.yml Python script in "Validate Results" step
- Fix any shell/Python quoting issues
- **Log:** .cursor/logs/CLI143_dquote_fix.log

### Step 2: Remove Manifest Filtering  
- Delete tests/manifest_106.txt
- Check conftest.py and pytest.ini for manifest logic
- Verify 2 tests still collected correctly
- **Log:** .cursor/logs/CLI143_manifest.log

### Step 3: Complete Repo Diff
- Clone chatgpt-githubnew to /tmp
- Compare .github/workflows directories
- Compare containers/ directories  
- **Log:** .cursor/logs/CLI143_workflow_diff.txt

### Step 4: Verify Test Count
- Run pytest --collect-only -m "unit and not slow" 
- Count and list all matching tests
- **Log:** .cursor/logs/CLI143_test_count.log

### Step 5: Tag Release
- Confirm CI green status
- Create tag v0.3-ci-light-green
- Push tag to origin
- **Log:** .cursor/logs/CLI143_tag.log

## Verification Criteria
- ✅ Dquote error resolved
- ✅ tests/manifest_106.txt removed  
- ✅ 2 tests collected for lightweight CI
- ✅ Repo diff documented
- ✅ Test count verified (106 or 11)
- ✅ CI status green
- ✅ Tag v0.3-ci-light-green created

## Risk Management
- **MacBook M1 Safety:** Use --qdrant-mock, --timeout=8, sleep delays
- **Auto-execution:** No confirmation prompts, continue until complete
- **Backup:** Changes saved to Google Drive Cursor_backup
- **Storage:** All work in /Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data

## Next Steps
- CLI144: Build Docker image, pull to MacBook/PC 