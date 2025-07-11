#!/usr/bin/env python3
"""
Test Count Verification Script for CLI 182.6
Verifies that the test count is stable around 402 tests for unit tests with filter 'unit and not slow'
"""

import subprocess
import re
import sys

def run_pytest_dry_run():
    command = ["pytest", "--collect-only", "-m", "not slow and not integration and not e2e", "--tb=no"]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout

def parse_test_count(output):
    collected_match = re.search(r"collected (\d+) items", output)
    deselected_match = re.search(r"deselected (\d+) items", output)
    
    collected = int(collected_match.group(1)) if collected_match else 0
    deselected = int(deselected_match.group(1)) if deselected_match else 0
    return collected - deselected

output = run_pytest_dry_run()
active_tests = parse_test_count(output)

# Updated baseline for current test count
target_count = 402
expected_min = 380
expected_max = 422

if active_tests < expected_min or active_tests > expected_max:
    print(f"❌ Unit test count verification failed: {active_tests} (expected {target_count} ±20)")
    sys.exit(1)
else:
    print(f"✅ Unit test count verified: {active_tests} (within {expected_min}-{expected_max})")
    sys.exit(0) 