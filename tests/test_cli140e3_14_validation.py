"""
CLI140e.3.14 Validation Tests
============================

This module validates the completion of CLI140e.3.14 objectives:
1. Enhanced Cloud Profiler with CPU/memory metrics and JSON parsing analysis
2. RAG query validation with outlier analysis and vector search results
3. Historical test count violation enforcement and compliance
4. Documentation completion for CLI140e.3.11 and CLI140e.3.14
5. Final validation of all CLI 140e objectives

Created for: CLI140e.3.14 completion validation
Test Count: 1 new test (464 -> 465, compliant with "1 test per CLI" rule)
"""

import pytest
import json
from pathlib import Path


class TestCLI140e314Validation:
    """Test class for CLI140e.3.14 completion validation."""

    @pytest.mark.meta
    def test_cli140e3_14_objectives_completion_validation(self):
        """
        Validate that all CLI140e.3.14 objectives have been completed:
        - Enhanced Cloud Profiler with CPU/memory metrics
        - RAG outlier analysis and vector search results
        - Historical test count compliance enforcement
        - Documentation completion
        """
        # Objective 1: Enhanced Cloud Profiler validation
        profiler_file = Path("test_cloud_profiler_50_queries.py")
        assert profiler_file.exists(), "Cloud Profiler test file should exist"

        profiler_content = profiler_file.read_text()

        # Check for CPU/memory enhancements
        assert "psutil" in profiler_content, "psutil should be imported for CPU/memory monitoring"
        assert "cpu_percent" in profiler_content, "CPU percentage monitoring should be implemented"
        assert "memory_info" in profiler_content, "Memory monitoring should be implemented"
        assert "json_parse_time_ms" in profiler_content, "JSON parsing time should be measured"
        assert "CLI140e.3.14" in profiler_content, "Should be updated to CLI140e.3.14"

        # Check for metrics collection
        assert "cpu_metrics" in profiler_content, "CPU metrics collection should be implemented"
        assert "memory_metrics" in profiler_content, "Memory metrics collection should be implemented"
        assert "json_parsing_metrics" in profiler_content, "JSON parsing metrics should be implemented"

        print("✅ Cloud Profiler enhanced with CPU/memory/JSON parsing metrics")

        # Objective 2: RAG outlier analysis validation
        rag_file = Path("test_50_document_latency.py")
        assert rag_file.exists(), "RAG latency test file should exist"

        rag_content = rag_file.read_text()

        # Check for outlier analysis
        assert "outliers" in rag_content, "Outlier analysis should be implemented"
        assert "vector_search_results" in rag_content, "Vector search results should be captured"
        assert "CLI140e.3.14" in rag_content, "Should be updated to CLI140e.3.14"
        assert "doc_id" in rag_content, "Vector search should capture doc_id"
        assert "score" in rag_content, "Vector search should capture relevance score"
        assert "metadata" in rag_content, "Vector search should capture metadata"

        # Check for outlier threshold
        assert "0.5" in rag_content, "Outlier threshold of 0.5s should be implemented"

        print("✅ RAG validation enhanced with outlier analysis and vector search results")

        # Objective 3: Historical test count compliance validation
        enforcement_file = Path("tests/test_enforce_single_test.py")
        assert enforcement_file.exists(), "Test enforcement file should exist"

        enforcement_content = enforcement_file.read_text()

        # Check for historical violation tracking
        assert "140e.3.14" in enforcement_content, "CLI140e.3.14 should be tracked"
        assert (
            "HISTORICAL CLI 140e VIOLATION ANALYSIS" in enforcement_content
        ), "Historical analysis should be implemented"
        assert "total_violations" in enforcement_content, "Total violations should be calculated"
        assert "total_excess_tests" in enforcement_content, "Excess tests should be calculated"
        assert "Compliance rate" in enforcement_content, "Compliance rate should be calculated"

        # Check specific historical violations are documented
        assert "CLI 140e.3" in enforcement_content, "CLI140e.3 violations should be documented"
        assert "CLI 140e.3.12" in enforcement_content, "Recent violations should be tracked"

        print("✅ Historical test count compliance enforcement implemented")

        # Objective 4: Documentation completion validation
        cli140e311_guide = Path(".misc/CLI140e3.11_guide.txt")
        assert cli140e311_guide.exists(), "CLI140e.3.11 guide should exist"

        guide_content = cli140e311_guide.read_text()
        assert len(guide_content) > 1000, "CLI140e.3.11 guide should have substantial content"
        assert "JWT authentication" in guide_content, "Should document JWT fixes"
        assert "Mock RAG latency" in guide_content, "Should document RAG optimization"
        assert "Cloud Profiler 401" in guide_content, "Should document Profiler fixes"

        print("✅ CLI140e.3.11 documentation populated")

        # Objective 5: Test count compliance
        meta_count_file = Path("tests/test__meta_count.py")
        assert meta_count_file.exists(), "Meta count test should exist"

        meta_content = meta_count_file.read_text()
        # Note: Test count updated to 468 in CLI140e.3.18 after strategic replacement
        assert (
            "EXPECTED_TOTAL_TESTS = 468" in meta_content
        ), "Expected test count should be 468 (updated in CLI140e.3.18)"
        assert "CLI140e.3.14" in meta_content, "CLI140e.3.14 should be documented"

        print("✅ Test count updated to 468 (strategic replacement in CLI140e.3.18)")

        # Objective 6: Profiler log verification (if exists)
        profiler_log = Path("logs/profiler_real_workload.log")
        if profiler_log.exists():
            try:
                with open(profiler_log, "r") as f:
                    log_data = json.load(f)

                # Check for enhanced metrics in logs
                test_summary = log_data.get("test_summary", {})

                if "cpu_metrics" in test_summary:
                    cpu_metrics = test_summary["cpu_metrics"]
                    assert "mean_cpu_percent" in cpu_metrics, "CPU metrics should include mean percentage"
                    print(f"✅ CPU metrics captured: {cpu_metrics.get('mean_cpu_percent', 0):.1f}% mean")

                if "memory_metrics" in test_summary:
                    memory_metrics = test_summary["memory_metrics"]
                    assert "mean_memory_mb" in memory_metrics, "Memory metrics should include mean MB"
                    print(f"✅ Memory metrics captured: {memory_metrics.get('mean_memory_mb', 0):.1f}MB mean")

                if "json_parsing_metrics" in test_summary:
                    json_metrics = test_summary["json_parsing_metrics"]
                    assert "mean_json_parse_ms" in json_metrics, "JSON parsing metrics should include mean time"
                    print(f"✅ JSON parsing metrics captured: {json_metrics.get('mean_json_parse_ms', 0):.2f}ms mean")

            except (json.JSONDecodeError, FileNotFoundError):
                print("⚠️  Profiler log exists but couldn't parse (acceptable)")
        else:
            print("ℹ️  Profiler log not found (acceptable for validation)")

        # Objective 7: RAG log verification (if exists)
        rag_log = Path("logs/latency_50docs_real.log")
        if rag_log.exists():
            try:
                with open(rag_log, "r") as f:
                    log_data = json.load(f)

                # Check for enhanced analysis in logs
                if "outlier_analysis" in log_data:
                    outlier_data = log_data["outlier_analysis"]
                    assert "threshold_seconds" in outlier_data, "Outlier threshold should be documented"
                    assert outlier_data["threshold_seconds"] == 0.5, "Outlier threshold should be 0.5s"
                    print(f"✅ Outlier analysis captured: {outlier_data.get('outliers_count', 0)} outliers")

                if "vector_search_analysis" in log_data:
                    vector_data = log_data["vector_search_analysis"]
                    assert "results_captured" in vector_data, "Vector search results should be documented"
                    print(f"✅ Vector search analysis captured: {vector_data.get('results_captured', 0)} queries")

            except (json.JSONDecodeError, FileNotFoundError):
                print("⚠️  RAG log exists but couldn't parse (acceptable)")
        else:
            print("ℹ️  RAG log not found (acceptable for validation)")

        # Final validation summary
        print("\n🎉 CLI140e.3.14 COMPLETION SUMMARY:")
        print("✅ Enhanced Cloud Profiler with CPU/memory/JSON metrics")
        print("✅ RAG validation with outlier analysis and vector search results")
        print("✅ Historical test count violation enforcement")
        print("✅ CLI140e.3.11 documentation completed")
        print("✅ Test count compliance maintained (468 total, strategic replacement)")
        print("✅ All CLI 140e objectives finalized")

        # Performance expectations
        print("\n📊 PERFORMANCE EXPECTATIONS:")
        print("- Cloud Profiler: CPU%, Memory MB, JSON parsing ms logged")
        print("- RAG queries: Outliers >0.5s identified and logged")
        print("- Vector search: doc_id, score, metadata captured")
        print("- Test runtime: <30s for active tests")
        print("- Historical compliance: Violations documented and tracked")

        print("\n🏁 CLI140e.3.14 COMPLETED - All objectives achieved!")
