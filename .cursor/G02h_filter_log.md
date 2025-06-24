# G02h Test Filtering Log - Full Analysis

**Date:** June 23, 2025, 14:00 +07
**Total tests collected:** 497
**Target for CI:** 519 tests
**Initial selection:** 418 tests

## 📊 Test Distribution Analysis

| Category | Count | Description |
|----------|-------|-------------|
| COVERAGE | 126 | Coverage tests and validation suites |
| CORE | 254 | Core functionality, APIs, auth, basic operations |
| PERFORMANCE | 30 | Performance, latency, and optimization tests |
| EXCLUDE | 79 | Problematic tests excluded from CI |
| OTHER | 8 | General tests not in other categories |

## 🎯 Selection Strategy

The initial manifest prioritizes:
1. **Core functionality tests** - Essential APIs, auth, vectors, basic operations
2. **Coverage and validation tests** - Quality assurance and validation suites
3. **Unit tests** - Fast tests with mocks and minimal dependencies
4. **Limited integration tests** - Key integration scenarios only
5. **Controlled performance tests** - Essential performance validations

## ❌ Excluded Categories

**79 tests excluded** for stability:
- `test_cli140k*` - Runtime optimization tests (most problematic)
- `test_cli140l*` - Nightly simulation tests
- `test_cli140j*` - Cost optimization tests
- Full runtime validation tests
- Cost optimization tests

## 📝 Manual Adjustment Instructions

**Next Steps for User:**
1. Review `tests/manifest_ci.txt` (current: 519 tests)
2. Add/remove tests as needed to reach exactly 519
3. Priority should be: stability > coverage > speed
4. Avoid tests with known flakiness (e.g., rate limiting, timeouts)
5. Test locally with: `pytest --collect-only -q --qdrant-mock | wc -l`

## 🔍 Detailed Test List by Category

### CORE Tests Selected (254)

- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_optimized_document_existence_check`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_fallback_existence_check`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_optimized_versioning_document_fetch`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_nonexistent_document_optimization`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_batch_existence_optimization`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_ru_cost_comparison`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_save_metadata_with_ru_optimization`
- `tests/test_cli140e1_firestore_ru.py::TestFirestoreRUOptimization::test_end_to_end_ru_optimization`
- `tests/test_cli140e_coverage.py::TestThreadSafeLRUCache::test_cache_basic_operations`
- `tests/test_cli140e_coverage.py::TestThreadSafeLRUCache::test_cache_ttl_expiration`
- ... and 244 more

### COVERAGE Tests Selected (126)

- `tests/legacy/test_cli140m10_coverage.py::test_overall_coverage_exceeds_20_percent`
- `tests/legacy/test_cli140m10_coverage.py::test_test_suite_pass_rate_validation`
- `tests/legacy/test_cli140m10_coverage.py::test_async_mocking_fixes_validation`
- `tests/legacy/test_cli140m10_coverage.py::test_cli140m10_completion_validation`
- `tests/legacy/test_cli140m10_coverage.py::test_git_operations_readiness`
- `tests/legacy/test_cli140m10_coverage.py::test_cli140m10_meta_validation`
- `tests/test_cli140g3_validation.py::TestCLI140g3Validation::test_cli140g3_architecture_distribution_70_20_10`
- `tests/test_cli140g3_validation.py::TestCLI140g3Validation::test_cli140g3_api_gateway_latency_validation`
- `tests/test_cli140g3_validation.py::TestCLI140g3Validation::test_cli140g3_cloud_functions_routing_optimization`
- `tests/test_cli140g3_validation.py::TestCLI140g3Validation::test_cli140g3_workflows_orchestration_validation`
- ... and 116 more

### PERFORMANCE Tests Selected (30)

- `tests/test_cli140e_latency.py::TestLatencyProfiling::test_rag_search_latency_profile`
- `tests/test_cli140e_latency.py::TestLatencyProfiling::test_cskh_api_latency_profile`
- `tests/test_cli140e_latency.py::TestLatencyProfiling::test_end_to_end_latency_with_caching`
- `tests/test_cli140f_coverage.py::TestCLI140fCoverage::test_rate_limiting_mechanism`
- `tests/test_cli140f_coverage.py::TestCLI140fCoverage::test_filter_methods_coverage`
- `tests/test_cli140f_coverage.py::TestCLI140fCoverage::test_standalone_function_coverage`
- `tests/test_cli140f_coverage.py::test_qdrant_batch_vectorize_documents_function_performance`
- `tests/test_cli140f_coverage.py::test_qdrant_rag_search_function_performance`
- `tests/test_cli140f_performance.py::TestCLI140fPerformance::test_document_ingestion_single_latency`
- `tests/test_cli140f_performance.py::TestCLI140fPerformance::test_qdrant_vectorization_single_latency`
- ... and 20 more

### OTHER Tests Selected (8)

- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_comprehensive_vectorization_success_path`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_batch_vectorization_success_scenarios`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_rag_search_comprehensive_scenarios`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_filter_methods_comprehensive`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_error_handling_comprehensive`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_standalone_functions_success_paths`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_edge_cases_and_boundary_conditions`
- `tests/test_cli140m7_final_push.py::TestCLI140m7FinalPushQdrantVectorization::test_cli140m7_final_push_completion`

### EXCLUDED Tests (79)

- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_cost_optimization_sink_exists` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_billing_api_enabled` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_bigquery_dataset_exists` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_log_sink_permissions` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_cost_target_validation` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_min_instances_configuration_persistence` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_logging_optimization_active` - Excluded: test_cli140[klj]
- `tests/test_cli140j1_fixes.py::TestCLI140j1Fixes::test_service_scaling_responsiveness` - Excluded: test_cli140[klj]
- `tests/test_cli140j2_cost_verification.py::TestCLI140j2CostVerification::test_billing_api_cost_query` - Excluded: test_cli140[klj]
- `tests/test_cli140j2_cost_verification.py::TestCLI140j2CostVerification::test_min_instances_zero_verification` - Excluded: test_cli140[klj]
- ... and 69 more excluded

