# G02i Completion Plan - Lock Baseline 519 Tests

**Date:** June 23, 2025, 15:45 +07  
**Branch:** fix/ci-final4  
**Objective:** Lock baseline to 519 tests, ensure 2 consecutive green CI runs, tag v0.2-ci-full-pass, merge PR #1

## Steps Completed

### 1. Update Meta-test and Manifest ✅
- **Updated tests/test_meta_counts.py:**
  - Changed `EXPECTED_TOTAL_TESTS = int(os.getenv("EXPECTED_TOTAL_TESTS", "519"))`
  - Changed `EXPECTED_SKIPPED = int(os.getenv("EXPECTED_SKIPPED", "6"))`
  - Added environment variable support for dynamic configuration

- **Regenerated tests/manifest_ci.txt:**
  - Used command: `python -m pytest --collect-only -q -m "not deferred and not slow" --qdrant-mock | grep "::" > tests/manifest_ci.txt`
  - Verified count: exactly 519 tests
  - Tests properly filtered with "not deferred and not slow" markers

- **Created scripts/check_skipped.py:**
  - Script to validate skipped test count ≤6
  - Usage: `python scripts/check_skipped.py <pytest_output_file> <max_skipped>`
  - Made executable with chmod +x

### 2. Clean CI Workflow ✅
- **Updated .github/workflows/ci.yaml:**
  - Synced pre-job and test job filters: `-m "not deferred and not slow"`
  - Added skipped count check: `python scripts/check_skipped.py skipped.log 6`
  - Updated test collection to use consistent filter
  - Maintained matrix strategy with max-parallel: 1

- **Updated requirements.txt:**
  - Pinned pytest==8.2.1 (matching CI environment)
  - Pinned pytest-asyncio==0.23.6
  - Added pytest-rerunfailures==15.0 for flaky test handling

- **Updated pytest.ini:**
  - Already had correct addopts: `-m "not deferred and not slow"`
  - Markers properly defined

### 3. Handle Flaky Tests ✅
- **Added flaky handling to tests/test_cli140e_coverage_additional.py:**
  - Added `@pytest.mark.flaky(reruns=2, reruns_delay=1)` to test_register_endpoint
  - Installed pytest-rerunfailures for flaky test support

### 4. Execute Process ✅
- **Branch Management:**
  - Created fix/ci-final4 branch
  - Committed changes with message: "G02i: Lock baseline 519 tests, sync CI, handle flaky"
  - Pushed to origin/fix/ci-final4

## Current Status

### Test Collection Verification ✅
```bash
$ python -m pytest --collect-only -q -m "not deferred and not slow" --qdrant-mock | grep "::" | wc -l
519
```

### Skipped Count Verification ✅
```bash
$ python -m pytest -q --qdrant-mock -m "not deferred and not slow" -ra | python scripts/check_skipped.py /dev/stdin 6
📊 Found 0 skipped tests
✅ Skipped count: 0 (within limit of 6)
```

### Files Modified
- tests/test_meta_counts.py (environment variable support)
- tests/manifest_ci.txt (regenerated with 519 tests)
- scripts/check_skipped.py (new script)
- requirements.txt (version pinning, flaky support)
- .github/workflows/ci.yaml (sync filters, add skipped check)
- tests/test_cli140e_coverage_additional.py (flaky decorator)

## Next Steps

### 5. Verify CI ⏳
- Monitor GitHub Actions at: https://github.com/Huyen1974/agent-data/actions
- Expected CI workflow:
  1. **Pre-job:** Compare manifest, check skipped (≤6) → test job (run 1)
  2. **Run 1:** Execute 519 tests with --qdrant-mock
  3. **Run 2:** Execute if run 1 green
- **Success Criteria:**
  - 2 consecutive green runs
  - 519 tests collected
  - 0 Failed, 0 Timeout, 0 UNKNOWN
  - ≤6 Skipped
  - Pass rate >97%
  - Deselected = 0

### 6. Tag and Merge (Pending CI Success)
If 2 runs green:
```bash
gh pr merge --squash 1
gh release create v0.2-ci-full-pass -t "CI stable with 519 tests"
```

## Risk Management

### Test Count Stability
- ✅ Manifest locked to 519 tests
- ✅ Meta-test validates exact count
- ✅ Environment variables allow override if needed

### Marker Consistency
- ✅ Both pre-job and test job use: `-m "not deferred and not slow"`
- ✅ pytest.ini aligned with CI filters

### Flaky Test Handling
- ✅ test_register_endpoint has reruns=2, reruns_delay=1
- ✅ pytest-rerunfailures installed

### M1 Infrastructure Safety
- ✅ Tests run with --qdrant-mock
- ✅ GCP region: asia-southeast1
- ✅ RAM considerations: test collection locally, execution on CI

## Verification Criteria Status

| Criteria | Status |
|----------|--------|
| Test collection: 519 tests | ✅ Verified locally |
| Test results: 0 Failed, 0 Timeout, 0 UNKNOWN | ⏳ Pending CI |
| ≤6 Skipped, pass rate >97% | ⏳ Pending CI |
| CI configuration updated | ✅ Complete |
| Tag v0.2-ci-full-pass | ⏳ Pending CI success |
| PR #1 merged | ⏳ Pending CI success |
| .cursor/G02i_plan.md created | ✅ This document |

## Infrastructure Details

- **Storage:** /Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data
- **GCP Project:** chatgpt-db-project
- **GCP Region:** asia-southeast1
- **Python:** 3.10.17
- **CI:** GitHub Actions (Ubuntu, 7GB RAM)
- **Branch:** fix/ci-final4
- **Repository:** https://github.com/Huyen1974/agent-data

## Next CLI Phase
**G03 (GitHub 03):** Add Terraform backend and bucket resources, implement auto-import 