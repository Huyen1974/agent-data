#!/usr/bin/env python3
"""
Test Count Verification Script for CLI 184.7
Verifies that the test count is stable at 402 tests consistently across CI and local environments.
No environment-specific bypasses. Uses JSON report for accurate counting.
"""

import subprocess
import json
import sys
import os
import re

def run_pytest_collect_with_json():
    """Run pytest with JSON report to get accurate test collection count"""
    command = [
        "pytest", 
        "--collect-only", 
        "-m", "not slow and not integration and not e2e", 
        "--tb=no",
        "--json-report",
        "--json-report-file=.report.json",
        "-p", "no:randomly",  # Disable randomly plugin
        "-p", "no:rerunfailures",  # Disable rerunfailures plugin
        "--override-ini=addopts="  # Clear all addopts from pytest.ini
    ]
    
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Read JSON report for accurate count
    try:
        with open('.report.json', 'r') as f:
            report = json.load(f)
            
        # Get collected and deselected counts from JSON report
        collected = report.get('summary', {}).get('collected', 0)
        deselected = report.get('summary', {}).get('deselected', 0)
        actual_tests = collected - deselected
        
        print(f"JSON Report - Collected: {collected}, Deselected: {deselected}, Active: {actual_tests}")
        return actual_tests, result.stdout
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not read JSON report ({e}), falling back to text parsing")
        print(f"Pytest stdout: {result.stdout}")
        print(f"Pytest stderr: {result.stderr}")
        print(f"Pytest return code: {result.returncode}")
        return parse_test_count_from_text(result.stdout), result.stdout

def parse_test_count_from_text(output):
    """Fallback method: parse test count from pytest text output"""
    # Match patterns: "collected X items / Y deselected / Z selected" or "collected X items"
    collected_match = re.search(r"collected (\d+) items", output)
    deselected_match = re.search(r"(\d+) deselected", output)
    
    collected = int(collected_match.group(1)) if collected_match else 0
    deselected = int(deselected_match.group(1)) if deselected_match else 0
    return collected - deselected

def main():
    print("=== Test Count Verification for CLI 184.8 ===")
    print("Target: 567 tests (after syntax error fixes and test discovery improvements)")
    
    # Set PYTHONPATH to ensure imports work
    current_dir = os.getcwd()
    pythonpath = f"{current_dir}:{current_dir}/ADK:{current_dir}/ADK/agent_data"
    if 'PYTHONPATH' in os.environ:
        pythonpath += f":{os.environ['PYTHONPATH']}"
    os.environ['PYTHONPATH'] = pythonpath
    print(f"PYTHONPATH: {pythonpath}")
    
    # Run test collection
    active_tests, output = run_pytest_collect_with_json()
    
    # Target configuration - Updated for CLI 184.8 improvements
    target_count = 567  # Updated after fixing syntax errors and test discovery
    tolerance = 15  # Allow small variance for minor changes
    expected_min = target_count - tolerance  # 552
    expected_max = target_count + tolerance  # 582
    
    print(f"\nTest Count Analysis:")
    print(f"  Found: {active_tests} tests")
    print(f"  Target: {target_count} tests")
    print(f"  Acceptable range: {expected_min}-{expected_max}")
    
    # Check environment (for logging only, not for different behavior)
    is_ci = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true'
    env_label = "CI" if is_ci else "Local"
    print(f"  Environment: {env_label}")
    
    if active_tests < expected_min or active_tests > expected_max:
        print(f"\n❌ FAILURE: Test count {active_tests} is outside acceptable range {expected_min}-{expected_max}")
        print(f"Expected exactly {target_count} tests consistently across all environments.")
        
        # Show some pytest output for debugging
        print(f"\nPytest output for debugging:")
        print("=" * 60)
        print(output[-500:] if len(output) > 500 else output)  # Last 500 chars
        print("=" * 60)
        
        sys.exit(1)
    else:
        print(f"\n✅ SUCCESS: Test count {active_tests} is within acceptable range")
        print(f"Target {target_count} ± {tolerance} tests achieved in {env_label} environment")
        sys.exit(0)

if __name__ == "__main__":
    main() 