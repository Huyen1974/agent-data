"""
CLI140m.15 Validation Test
==========================

This test validates that CLI140m.15 objectives are met:
- Pass rate ≥95% (≤26 failures out of 565 tests)
- Coverage ≥80% for qdrant_vectorization_tool.py
- Overall coverage ≥70%
- Deferred tests properly excluded from main suite
"""

import pytest
import subprocess
import json
import os


class TestCLI140m15Validation:
    """Validation tests for CLI140m.15 objectives."""

    def test_pass_rate_target_validation(self):
        """Validate that pass rate meets ≥95% target."""
        # Run full test suite to get pass rate
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--tb=no", "-q"
        ], capture_output=True, text=True)
        
        # Parse the output to get test results
        output_lines = result.stdout.split('\n')
        summary_line = [line for line in output_lines if 'failed' in line and 'passed' in line]
        
        if summary_line:
            summary = summary_line[-1]  # Get the last summary line
            
            # Extract numbers from summary like "41 failed, 523 passed, 17 skipped"
            parts = summary.split(',')
            failed_count = 0
            passed_count = 0
            total_count = 0
            
            for part in parts:
                part = part.strip()
                if 'failed' in part:
                    failed_count = int(part.split()[0])
                elif 'passed' in part:
                    passed_count = int(part.split()[0])
                elif 'skipped' in part:
                    skipped_count = int(part.split()[0])
            
            total_count = failed_count + passed_count
            pass_rate = (passed_count / total_count) * 100 if total_count > 0 else 0
            
            # Validate pass rate
            target_pass_rate = 95.0
            assert pass_rate >= target_pass_rate, f"Pass rate {pass_rate:.1f}% below target {target_pass_rate}%"
            
            # Validate failure count
            max_failures = 26  # 5% of ~520 active tests
            assert failed_count <= max_failures, f"Too many failures: {failed_count} (should be ≤{max_failures})"
            
            print(f"✅ Pass rate validation passed:")
            print(f"   Pass rate: {pass_rate:.1f}% (≥{target_pass_rate}% target)")
            print(f"   Passed: {passed_count}, Failed: {failed_count}, Total: {total_count}")
            
        else:
            pytest.fail("Could not parse test results from pytest output")

    def test_coverage_target_validation(self):
        """Validate that coverage targets are met."""
        # Run coverage test on target modules
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--cov=ADK/agent_data/", 
            "--cov-report=json:.coverage_validation.json",
            "--cov-report=term-missing",
            "-q",
            "tests/test_cli140m13_coverage.py",
            "tests/test_cli140m14_coverage.py", 
            "tests/test_cli140m11_coverage.py",
            "tests/test_cli140m1_coverage.py"
        ], capture_output=True, text=True)
        
        # Read coverage data
        if os.path.exists('.coverage_validation.json'):
            with open('.coverage_validation.json', 'r') as f:
                coverage_data = json.load(f)
            
            # Extract coverage for target modules
            files = coverage_data.get('files', {})
            
            target_modules = {
                'ADK/agent_data/tools/qdrant_vectorization_tool.py': 80,
                'ADK/agent_data/tools/document_ingestion_tool.py': 80,
                'ADK/agent_data/api_mcp_gateway.py': 80
            }
            
            coverage_results = {}
            for module_path, target_coverage in target_modules.items():
                if module_path in files:
                    file_data = files[module_path]
                    coverage_percent = file_data['summary']['percent_covered']
                    coverage_results[module_path] = coverage_percent
                    
                    print(f"📊 {module_path}: {coverage_percent:.1f}% (target: {target_coverage}%)")
                    
                    # Only enforce 80% for qdrant_vectorization_tool.py for now
                    if 'qdrant_vectorization_tool.py' in module_path:
                        assert coverage_percent >= target_coverage, f"{module_path} coverage {coverage_percent:.1f}% below target {target_coverage}%"
                else:
                    print(f"⚠️  {module_path}: Not found in coverage data")
            
            # Check overall coverage
            overall_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
            target_overall = 70
            assert overall_coverage >= target_overall, f"Overall coverage {overall_coverage:.1f}% below target {target_overall}%"
            
            print(f"✅ Coverage validation results:")
            print(f"   Overall coverage: {overall_coverage:.1f}% (≥{target_overall}% target)")
            for module, coverage in coverage_results.items():
                module_name = module.split('/')[-1]
                print(f"   {module_name}: {coverage:.1f}%")
            
            # Clean up
            os.remove('.coverage_validation.json')
            
        else:
            pytest.fail("Coverage data file not generated")

    def test_deferred_tests_validation(self):
        """Validate that deferred tests are properly excluded from main suite."""
        # Check active test count
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--collect-only", "-q",
            "-m", "not slow and not deferred"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Active test collection should succeed"
        
        # Count active tests
        output_lines = result.stdout.split('\n')
        collection_line = [line for line in output_lines if 'tests collected' in line]
        
        if collection_line:
            summary = collection_line[0]
            if '/' in summary:
                active_count = int(summary.split('/')[0].strip())
                total_count = int(summary.split('/')[1].split()[0])
                deferred_count = total_count - active_count
            else:
                active_count = int(summary.split()[0])
                deferred_count = 0
            
            # Validate active test count is reasonable
            assert active_count <= 260, f"Too many active tests: {active_count} (should be ≤260)"
            assert deferred_count >= 300, f"Not enough deferred tests: {deferred_count} (should be ≥300)"
            
            print(f"✅ Deferred tests validation passed:")
            print(f"   Active tests: {active_count} (≤260 target)")
            print(f"   Deferred tests: {deferred_count} (≥300 target)")
            
        else:
            pytest.fail("Could not parse test collection summary")

    def test_cli140m15_objectives_summary(self):
        """Document CLI140m.15 objectives and current status."""
        objectives = {
            "primary_objectives": {
                "pass_rate": "≥95% (≤26 failures)",
                "qdrant_vectorization_coverage": "≥80%",
                "overall_coverage": "≥70%",
                "deferred_tests": "≥300 tests deferred"
            },
            "secondary_objectives": {
                "api_gateway_coverage": "≥80% (stretch goal)",
                "document_ingestion_coverage": "≥80% (stretch goal)",
                "test_optimization": "≤260 active tests",
                "sentinel_test": "test_no_deferred.py passes"
            },
            "git_operations": {
                "commit_required": True,
                "tag_required": "cli140m15_progress_achieved",
                "guide_documentation": ".misc/CLI140m15_guide.txt"
            }
        }
        
        # This test documents the objectives
        assert objectives["primary_objectives"]["pass_rate"] == "≥95% (≤26 failures)"
        assert objectives["primary_objectives"]["qdrant_vectorization_coverage"] == "≥80%"
        assert objectives["git_operations"]["commit_required"] is True
        
        print("📋 CLI140m.15 Objectives Summary:")
        print("   Primary Objectives:")
        for key, value in objectives["primary_objectives"].items():
            print(f"     {key}: {value}")
        print("   Secondary Objectives:")
        for key, value in objectives["secondary_objectives"].items():
            print(f"     {key}: {value}")
        print("   Git Operations:")
        for key, value in objectives["git_operations"].items():
            print(f"     {key}: {value}")

    def test_cli140m15_completion_readiness(self):
        """Test readiness for CLI140m.15 completion."""
        # This is a meta-test that checks if we're ready for completion
        
        # Check that key test files exist
        required_files = [
            "tests/test_cli140m13_coverage.py",
            "tests/test_cli140m14_coverage.py", 
            "tests/test_no_deferred.py",
            "tests/test_cli140m15_validation.py"
        ]
        
        for file_path in required_files:
            assert os.path.exists(file_path), f"Required test file missing: {file_path}"
        
        # Check that we have reasonable test counts
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--collect-only", "-q"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Test collection should succeed"
        
        output_lines = result.stdout.split('\n')
        collection_line = [line for line in output_lines if 'tests collected' in line]
        
        if collection_line:
            summary = collection_line[0]
            total_tests = int(summary.split()[0])
            
            # Should have substantial test suite
            assert total_tests >= 565, f"Test suite too small: {total_tests} tests (expected ≥565)"
            assert total_tests <= 600, f"Test suite too large: {total_tests} tests (expected ≤600)"
            
            print(f"✅ CLI140m.15 completion readiness:")
            print(f"   Total tests: {total_tests}")
            print(f"   Required files: All present")
            print(f"   Ready for completion: Yes")
            
        else:
            pytest.fail("Could not determine total test count")


if __name__ == "__main__":
    # Run validation tests directly
    pytest.main([__file__, "-v"]) 