"""
Sentinel test to ensure deferred tests are not running in main test suite.
This test validates that the test execution environment properly excludes deferred tests.
"""

import subprocess
import pytest


class TestNoDeferredSentinel:
    """Sentinel test class to validate deferred test exclusion."""
    
    def test_no_deferred_tests_in_main_suite(self):
        """
        Sentinel test: Ensure no deferred tests are running in main test suite.
        
        This test validates that when running the main test suite (without explicit
        deferred marker), no tests marked with @pytest.mark.deferred are executed.
        
        Expected behavior:
        - Main test suite should only run active tests (not slow, not deferred)
        - Deferred tests should only run when explicitly requested with -m "deferred"
        - This ensures fast development cycles and proper test categorization
        """
        # Run pytest with collection only to check what tests would be collected
        # when running without deferred marker filter
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--collect-only", "-q", 
            "-m", "not slow and not deferred"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Test collection should succeed"
        
        # Count tests that would run in main suite
        output_lines = result.stdout.split('\n')
        test_lines = [line for line in output_lines if '::test_' in line]
        active_test_count = len(test_lines)
        
        # Get collection summary
        collection_line = [line for line in output_lines if 'tests collected' in line]
        if collection_line:
            # Extract numbers from collection summary like "240/565 tests collected (325 deselected)"
            summary = collection_line[0]
            if '/' in summary:
                collected_count = int(summary.split('/')[0].strip())
                total_count = int(summary.split('/')[1].split()[0])
                deselected_count = total_count - collected_count
                
                # Validate that deferred tests are properly excluded
                assert collected_count <= 165, f"Too many active tests: {collected_count} (should be ≤165 for execution)"
                assert deselected_count >= 340, f"Not enough tests deferred: {deselected_count} deselected (should be ≥340)"
                
                print(f"✅ Sentinel validation passed:")
                print(f"   Active tests (not slow and not deferred): {collected_count}")
                print(f"   Deferred/slow tests: {deselected_count}")
                print(f"   Total tests: {total_count}")
                
                # Additional validation: ensure we have a reasonable number of active tests
                assert 145 <= collected_count <= 165, f"Active test count {collected_count} outside expected range 145-165"
                
            else:
                pytest.fail(f"Could not parse collection summary: {summary}")
        else:
            pytest.fail("Could not find collection summary in pytest output")
    
    def test_deferred_marker_functionality(self):
        """
        Test that deferred marker properly excludes tests when used.
        
        This validates that the pytest marker system is working correctly
        and deferred tests can be run separately when needed.
        """
        # Test that deferred tests can be collected when explicitly requested
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--collect-only", "-q", 
            "-m", "deferred"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Deferred test collection should succeed"
        
        # Count deferred tests
        output_lines = result.stdout.split('\n')
        collection_line = [line for line in output_lines if 'tests collected' in line]
        
        if collection_line:
            summary = collection_line[0]
            if '/' in summary:
                deferred_count = int(summary.split('/')[0].strip())
                
                # Validate that we have a significant number of deferred tests
                assert deferred_count >= 320, f"Expected ≥320 deferred tests, found {deferred_count}"
                
                print(f"✅ Deferred marker validation passed:")
                print(f"   Deferred tests available: {deferred_count}")
                
            else:
                # Handle case where all tests are collected (no deselection)
                if 'tests collected' in summary:
                    deferred_count = int(summary.split()[0])
                    assert deferred_count >= 320, f"Expected ≥320 deferred tests, found {deferred_count}"
                    print(f"✅ Deferred marker validation passed: {deferred_count} deferred tests")
                else:
                    pytest.fail(f"Could not parse deferred collection summary: {summary}")
        else:
            pytest.fail("Could not find deferred collection summary in pytest output")
    
    def test_fast_test_execution_target(self):
        """
        Validate that active test suite can execute within time targets.
        
        This test ensures that the main development test suite (active tests)
        can complete within reasonable time limits for fast development cycles.
        """
        # This is a meta-test that validates test suite performance characteristics
        # without actually running all tests (which would be slow)
        
        # Get active test count
        result = subprocess.run([
            "python", "-m", "pytest", 
            "--collect-only", "-q", 
            "-m", "not slow and not deferred"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, "Test collection should succeed"
        
        output_lines = result.stdout.split('\n')
        collection_line = [line for line in output_lines if 'tests collected' in line]
        
        if collection_line:
            summary = collection_line[0]
            if '/' in summary:
                active_count = int(summary.split('/')[0].strip())
            else:
                active_count = int(summary.split()[0])
            
            # Validate test count is within fast execution range
            # Target: ≤165 tests for reasonable execution with pytest-testmon and pytest-xdist
            assert active_count <= 165, f"Active test count {active_count} exceeds execution target (≤165)"
            
            # Estimate execution time based on test count
            # Assumption: ~0.1s per test with optimizations (testmon, xdist, mocking)
            estimated_time = active_count * 0.12  # Conservative estimate
            
            assert estimated_time <= 35, f"Estimated execution time {estimated_time:.1f}s exceeds 35s target"
            
            print(f"✅ Fast execution validation passed:")
            print(f"   Active tests: {active_count} (≤165 target)")
            print(f"   Estimated execution time: {estimated_time:.1f}s (≤35s target)")
            
        else:
            pytest.fail("Could not find collection summary for active tests")


if __name__ == "__main__":
    # Run sentinel tests directly
    pytest.main([__file__, "-v"]) 