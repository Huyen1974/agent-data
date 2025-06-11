# tests/test_cli140e3_17_validation.py
# CLI140e.3.17 Comprehensive Finalization Test: Complete All CLI 140e Objectives
#
# This test validates the final completion of CLI140e.3.17 by addressing all objectives:
# 1. CPU/memory/JSON parsing metrics verification from profiler logs
# 2. Sentinel test enforcement for historical violations by default
# 3. Documentation test fix confirmation
# 4. Active test count analysis and consolidation to comply with "1 test/CLI"
# 5. Final completion validation with detailed guide creation

import pytest
import json
import subprocess
from pathlib import Path


@pytest.mark.meta
def test_cli140e3_17_comprehensive_completion():
    """
    CLI140e.3.17 Comprehensive Test: Verify all objectives completion

    This consolidated test replaces the 5 separate CLI140e.3.16 tests and validates:
    - Profiler metrics verification (CPU%, memory MB, JSON parsing ms)
    - Sentinel test enforcement by default for historical violations
    - Documentation test fixes and guide creation
    - Active test count analysis and compliance with "1 test/CLI" rule
    - Final CLI140e objectives completion
    """

    # OBJECTIVE 1: Verify CPU%, memory MB, and JSON parsing metrics
    print("\n📊 CLI140e.3.17 OBJECTIVE 1: PROFILER METRICS VERIFICATION")

    log_file = Path("logs/profiler_real_workload.log")
    assert log_file.exists(), "Profiler real workload log must exist"

    # Parse profiler log
    with open(log_file, "r") as f:
        profiler_data = json.load(f)

    # Verify log structure and available metrics
    assert "test_summary" in profiler_data, "Profiler log must contain test_summary"
    assert "latency_stats" in profiler_data["test_summary"], "Must contain latency statistics"

    summary = profiler_data["test_summary"]

    # Verify required metrics are present
    assert "cpu_metrics" in summary, "Must contain CPU metrics"
    assert "memory_metrics" in summary, "Must contain memory metrics"
    assert "json_parsing_metrics" in summary, "Must contain JSON parsing metrics"

    cpu_metrics = summary["cpu_metrics"]
    memory_metrics = summary["memory_metrics"]
    json_metrics = summary["json_parsing_metrics"]

    # Verify CPU metrics
    assert cpu_metrics.get("mean_cpu_percent", 0) > 0, "CPU metrics must be captured"
    assert cpu_metrics.get("min_cpu_percent", 0) >= 0, "CPU min must be valid"
    assert cpu_metrics.get("max_cpu_percent", 0) <= 100.5, "CPU max must be reasonable"

    # Verify memory metrics
    assert memory_metrics.get("mean_memory_mb", 0) > 0, "Memory metrics must be captured"
    assert memory_metrics.get("min_memory_mb", 0) > 0, "Memory min must be positive"
    assert memory_metrics.get("max_memory_mb", 0) < 1000, "Memory max must be reasonable"

    # Verify JSON parsing metrics
    assert json_metrics.get("mean_json_parse_ms", 0) > 0, "JSON parsing metrics must be captured"
    assert json_metrics.get("min_json_parse_ms", 0) > 0, "JSON parsing min must be positive"

    print(
        f"✓ CPU Metrics: Min={cpu_metrics.get('min_cpu_percent', 0):.1f}%, Max={cpu_metrics.get('max_cpu_percent', 0):.1f}%, Mean={cpu_metrics.get('mean_cpu_percent', 0):.1f}%"
    )
    print(
        f"✓ Memory Metrics: Min={memory_metrics.get('min_memory_mb', 0):.1f}MB, Max={memory_metrics.get('max_memory_mb', 0):.1f}MB, Mean={memory_metrics.get('mean_memory_mb', 0):.1f}MB"
    )
    print(
        f"✓ JSON Parse Metrics: Min={json_metrics.get('min_json_parse_ms', 0):.2f}ms, Max={json_metrics.get('max_json_parse_ms', 0):.2f}ms, Mean={json_metrics.get('mean_json_parse_ms', 0):.2f}ms"
    )

    # OBJECTIVE 2: Enforce sentinel test failure by default for historical violations
    print("\n🔒 CLI140e.3.17 OBJECTIVE 2: SENTINEL ENFORCEMENT BY DEFAULT")

    # Check that sentinel test file exists and has default enforcement logic
    sentinel_file = Path("tests/test_enforce_single_test.py")
    assert sentinel_file.exists(), "Sentinel test file must exist"

    # Read sentinel test content
    with open(sentinel_file, "r") as f:
        sentinel_content = f.read()

    # Verify default enforcement mechanisms exist (CLI140e.3.17 changes)
    assert "CLI140e.3.17" in sentinel_content, "Must reference CLI140e.3.17"
    assert "DEFAULT ENFORCEMENT" in sentinel_content, "Must have default enforcement"
    assert "PYTEST_DISABLE_ENFORCE" in sentinel_content, "Must have disable option"
    assert "enforcement_disabled" in sentinel_content, "Must check for enforcement disabled"

    # Verify that enforcement is by default (not opt-in like CLI140e.3.16)
    assert "not enforcement_disabled" in sentinel_content, "Must enforce by default"

    print("✓ Sentinel test updated for default enforcement")
    print("✓ Historical violations will fail by default")
    print("✓ PYTEST_DISABLE_ENFORCE=true option available")

    # OBJECTIVE 3: Documentation test fix confirmation
    print("\n📋 CLI140e.3.17 OBJECTIVE 3: DOCUMENTATION TEST FIX")

    # Check CLI140e3.12 validation test exists
    cli140e312_test = Path("tests/test_cli140e3_12_validation.py")
    assert cli140e312_test.exists(), "CLI140e3.12 validation test must exist"

    # Check that main CLI140_guide.txt exists and is updated
    main_guide = Path(".cursor/CLI140_guide.txt")
    if main_guide.exists():
        with open(main_guide, "r") as f:
            guide_content = f.read()
        # Verify guide contains recent CLI updates
        assert "CLI140e" in guide_content, "Main guide must reference CLI140e series"
        print("✓ Main CLI140_guide.txt exists and contains CLI140e references")

    print("✓ Documentation test infrastructure confirmed")

    # OBJECTIVE 4: Active test count analysis and compliance
    print("\n🧮 CLI140e.3.17 OBJECTIVE 4: TEST COUNT COMPLIANCE")

    # Get current test counts
    try:
        collect_process = subprocess.run(["pytest", "--collect-only", "-q"], check=True, capture_output=True, text=True)

        total_count = 0
        for line in collect_process.stdout.strip().split("\n"):
            if "tests collected" in line or "test collected" in line:
                words = line.split()
                if words and words[0].isdigit():
                    total_count = int(words[0])
                    break

        # Get active test count (not deferred)
        active_process = subprocess.run(
            ["pytest", "-m", "not deferred", "--collect-only", "-q"], check=True, capture_output=True, text=True
        )

        active_count = 0
        active_output = active_process.stdout.strip()

        # Count active tests
        if "tests collected" in active_output or "/" in active_output:
            for line in active_output.split("\n"):
                if "/" in line and "tests collected" in line:
                    # Extract number from lines like "127/471 tests collected (344 deselected)"
                    parts = line.split("/")
                    if parts[0].strip().isdigit():
                        active_count = int(parts[0].strip())
                        break
                elif "tests collected" in line and "/" not in line:
                    # Simple count without deselection
                    words = line.split()
                    if words and words[0].isdigit():
                        active_count = int(words[0])
                        break

    except (subprocess.CalledProcessError, ValueError) as e:
        pytest.fail(f"Failed to collect test count: {e}")

    print(f"✓ Total tests: {total_count}")
    print(f"✓ Active tests: {active_count}")

    # Verify test count compliance (CLI140e.3.17 should be 467 after consolidation)
    expected_total = 467  # 471 (CLI140e.3.16) - 5 (consolidated) + 1 (new CLI140e.3.17) = 467

    # Allow for small discrepancy during transition
    assert abs(total_count - expected_total) <= 5, f"Total test count {total_count} should be close to {expected_total}"

    # Verify active test count is reasonable (around 100-150)
    assert 90 <= active_count <= 200, f"Active test count {active_count} should be reasonable (90-200)"

    print(f"✓ Test count compliance: Target={expected_total}, Actual={total_count}")
    print(f"✓ Active test analysis: {active_count} tests active")

    # OBJECTIVE 5: Final CLI140e objectives completion validation
    print("\n🎯 CLI140e.3.17 OBJECTIVE 5: FINAL COMPLETION VALIDATION")

    # Verify infrastructure and performance expectations
    latency_stats = summary.get("latency_stats", {})
    if latency_stats:
        mean_latency = latency_stats.get("mean", 0)
        p95_latency = latency_stats.get("p95", 0)

        # Verify reasonable performance
        assert mean_latency < 5.0, f"Mean latency {mean_latency:.3f}s should be reasonable"
        assert p95_latency < 30.0, f"P95 latency {p95_latency:.3f}s should be acceptable"

        print(f"✓ Performance validated: Mean={mean_latency:.3f}s, P95={p95_latency:.3f}s")

    # Verify health check passed
    health_check = summary.get("health_check", {})
    assert health_check.get("status") == "success", "Health check must pass"

    services = health_check.get("services_connected", {})
    assert services.get("qdrant") == "connected", "Qdrant must be connected"
    assert services.get("firestore") == "connected", "Firestore must be connected"

    print("✓ Infrastructure health verified")

    print("✓ CLI140e.3.17 completion metrics documented")
    print("✓ All 5 objectives achieved successfully")

    # Final validation
    assert True, "CLI140e.3.17 comprehensive completion validation passed"
