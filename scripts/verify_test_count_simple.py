#!/usr/bin/env python3
"""
Simple Test Count Verification Script for CI Integration
========================================================

Verifies that the test count meets the target requirements by running pytest collection
and counting the results directly.

Usage:
    python scripts/verify_test_count_simple.py [expected_unit_count] [tolerance]
    
Arguments:
    expected_unit_count: Expected number of unit tests (default: 855)
    tolerance: Allowed deviation (default: 50)
"""

import subprocess
import sys
import os


def run_pytest_collection(marker_filter):
    """Run pytest collection with marker filter and return count."""
    cmd = [
        "python", "-m", "pytest", 
        "--collect-only", 
        "-q",
        "--tb=no"
    ]
    
    # Only add marker filter if it's not empty
    if marker_filter:
        cmd.extend(["-m", marker_filter])
    
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"
    
    try:
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True, 
                              env=env,
                              timeout=60)
        
        # Count test functions from output
        lines = result.stdout.split('\n')
        test_count = 0
        collected_info = ""
        
        for line in lines:
            if "::test_" in line:
                test_count += 1
            elif "tests collected" in line:
                collected_info = line
        
        # Also try to extract from summary line
        if collected_info:
            parts = collected_info.split()
            for i, part in enumerate(parts):
                if part.isdigit() and i < len(parts) - 1:
                    if "tests" in parts[i + 1] or "test" in parts[i + 1]:
                        summary_count = int(part)
                        if summary_count > 0:
                            test_count = summary_count
                            break
        
        return test_count, result.stderr
        
    except subprocess.TimeoutExpired:
        return 0, "Timeout during collection"
    except Exception as e:
        return 0, f"Error: {str(e)}"


def verify_test_count(expected_count=855, tolerance=50):
    """Verify test counts meet requirements."""
    print(f"Verifying test count...")
    print(f"Expected unit tests (not slow/integration/e2e): {expected_count}±{tolerance}")
    print("-" * 50)
    
    # Count unit tests (not slow, integration, or e2e)
    unit_count, unit_errors = run_pytest_collection("not slow and not integration and not e2e")
    print(f"Unit tests (not slow/integration/e2e): {unit_count}")
    
    # Count all tests
    all_count, all_errors = run_pytest_collection("")
    print(f"Total tests: {all_count}")
    
    # Count slow tests
    slow_count, slow_errors = run_pytest_collection("slow")
    print(f"Slow tests: {slow_count}")
    
    # Count integration tests
    integration_count, integration_errors = run_pytest_collection("integration")
    print(f"Integration tests: {integration_count}")
    
    # Count e2e tests
    e2e_count, e2e_errors = run_pytest_collection("e2e")
    print(f"E2E tests: {e2e_count}")
    
    # Check if unit test count is within tolerance
    expected_min = expected_count - tolerance
    expected_max = expected_count + tolerance
    
    success = expected_min <= unit_count <= expected_max
    
    if success:
        print(f"\n✓ Unit tests (not slow/integration/e2e): {unit_count} (target: {expected_count}±{tolerance})")
        print("✓ Test count verification PASSED")
        return True
    else:
        print(f"\n✗ Unit tests (not slow/integration/e2e): {unit_count} (expected: {expected_count}±{tolerance})")
        print("✗ Test count verification FAILED")
        
        # Show errors if any
        if unit_errors:
            print(f"\nErrors during unit test collection:")
            print(unit_errors[:500] + "..." if len(unit_errors) > 500 else unit_errors)
        
        return False


def main():
    """Main function."""
    expected_count = int(sys.argv[1]) if len(sys.argv) > 1 else 855
    tolerance = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    success = verify_test_count(expected_count, tolerance)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main() 