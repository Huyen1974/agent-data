# G2q Quick Scan Report
*Date: 24 Jun 2025 22:05 +07*
*Branch: scan/quick-collect-retry*

## Summary

✅ **Compile Check**: PASSED - No syntax errors in tests directory  
✅ **Collect-Only**: COMPLETED within 10s timeout (2.48s actual)  
⚠️  **Manifest vs Collected**: Significant differences detected

## Test Collection Statistics

| File | Line Count |
|------|------------|
| **Manifest (519 fixed)** | **514** |
| **Collected Tests** | **934** |
| **Missing Tests** | **200** |
| **Extra Tests** | **620** |

## Key Findings

### 1. Compilation Status
- **Result**: ✅ PASSED
- All test files compile without syntax errors

### 2. Collection Performance
- **Timeout**: 10s limit
- **Actual Time**: 2.48s
- **Status**: ✅ COMPLETED successfully
- **Total Collected**: 932 test nodes + 2 collection metadata lines = 934 lines

### 3. Manifest Comparison

#### Missing Tests (200 items - not in collected)
Tests present in manifest but not found during collection:
```
tests/legacy/test_cli140m10_coverage.py::test_cli140m10_meta_validation
tests/legacy/test_cli140m10_coverage.py::TestCLI140m10CoverageValidation::test_async_mocking_fixes_validation
tests/legacy/test_cli140m10_coverage.py::TestCLI140m10CoverageValidation::test_cli140m10_completion_validation
tests/legacy/test_cli140m10_coverage.py::TestCLI140m10CoverageValidation::test_git_operations_readiness
tests/legacy/test_cli140m10_coverage.py::TestCLI140m10CoverageValidation::test_overall_coverage_exceeds_20_percent
tests/legacy/test_cli140m10_coverage.py::TestCLI140m10CoverageValidation::test_test_suite_pass_rate_validation
tests/legacy/test_cli140m5_simple.py::TestCLI140m5CoverageValidation::test_cli140m5_completion_summary
tests/legacy/test_cli140m5_simple.py::TestCLI140m5CoverageValidation::test_cli140m5_coverage_targets
tests/legacy/test_cli140m5_simple.py::TestCLI140m5CoverageValidation::test_cli140m5_test_count_validation
tests/legacy/test_cli140m5_simple.py::TestCLI140m5DocumentIngestionToolFixed::test_document_ingestion_tool_advanced_methods
...
```
*→ Full list in missing.txt (200 total)*

#### Extra Tests (620 items - collected but not in manifest)
Tests found during collection but not in manifest:
```
tests/api/test_all_tags_lowercase_in_fixtures.py::test_all_tags_lowercase_in_fixtures
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_api_a2a_integration_flow
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_health_endpoint_no_services
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_pydantic_models_validation
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_query_vectors_invalid_request
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_query_vectors_service_unavailable
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_query_vectors_success
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_root_endpoint
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_save_document_invalid_request
tests/api/test_api_a2a_gateway.py::TestAPIAGateway::test_save_document_service_unavailable
...
```
*→ Full list in extra.txt (620 total)*

## Diagnostic Files Created

- `collected.txt` - All collected test node IDs (934 lines)
- `missing.txt` - Tests in manifest but not collected (200 lines)  
- `extra.txt` - Tests collected but not in manifest (620 lines)
- `counts.txt` - Line count summary for all files

## Recommendations

1. **Missing Tests (200)**: Mostly from `tests/legacy/` - need to investigate if these files/tests still exist
2. **Extra Tests (620)**: Many new tests in `tests/api/` not reflected in manifest - manifest may be outdated
3. **Next Steps**: The manifest appears significantly out of sync with current test suite

## Safety Compliance

✅ Ultra-light commands only  
✅ Hard 10s timeout respected  
✅ No full test suite execution  
✅ No code modifications made  
✅ Working tree left pristine
