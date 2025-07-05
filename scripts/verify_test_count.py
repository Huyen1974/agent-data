#!/usr/bin/env python3
"""
Test Count Verification Script for CI Integration
=================================================

Verifies that the test count meets the target requirements:
- Unit tests (not slow): ~157 tests (±10 tolerance)
- Total tests collected: ~941 tests

Usage:
    python scripts/verify_test_count.py [report_file] [expected_unit_count] [tolerance]
    
Arguments:
    report_file: JSON report file from pytest --json-report
    expected_unit_count: Expected number of unit tests (default: 157)
    tolerance: Allowed deviation (default: 10)
"""

import json
import sys
import os
from pathlib import Path


def load_test_report(report_file):
    """Load pytest JSON report."""
    if not os.path.exists(report_file):
        print(f"ERROR: Report file {report_file} not found")
        return None
    
    try:
        with open(report_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON report: {e}")
        return None


def count_tests_by_markers(report):
    """Count tests by their markers."""
    if not report or 'tests' not in report:
        print("ERROR: Invalid report format")
        return None
    
    unit_not_slow = 0
    unit_all = 0
    slow_tests = 0
    integration_tests = 0
    total_tests = len(report['tests'])
    
    for test in report['tests']:
        markers = test.get('markers', [])
        marker_names = [m['name'] for m in markers] if markers else []
        
        is_unit = 'unit' in marker_names
        is_slow = 'slow' in marker_names
        is_integration = 'integration' in marker_names
        
        if is_unit:
            unit_all += 1
            if not is_slow:
                unit_not_slow += 1
        
        if is_slow:
            slow_tests += 1
            
        if is_integration:
            integration_tests += 1
    
    return {
        'unit_not_slow': unit_not_slow,
        'unit_all': unit_all,
        'slow': slow_tests,
        'integration': integration_tests,
        'total': total_tests
    }


def verify_test_count(counts, expected_unit_count=157, tolerance=10):
    """Verify test counts meet requirements."""
    if not counts:
        return False, "Failed to count tests"
    
    unit_not_slow = counts['unit_not_slow']
    expected_min = expected_unit_count - tolerance
    expected_max = expected_unit_count + tolerance
    
    success = True
    messages = []
    
    # Check unit test count
    if expected_min <= unit_not_slow <= expected_max:
        messages.append(f"✓ Unit tests (not slow): {unit_not_slow} (target: {expected_unit_count}±{tolerance})")
    else:
        messages.append(f"✗ Unit tests (not slow): {unit_not_slow} (expected: {expected_unit_count}±{tolerance})")
        success = False
    
    # Report other counts
    messages.append(f"  Total unit tests: {counts['unit_all']}")
    messages.append(f"  Slow tests: {counts['slow']}")
    messages.append(f"  Integration tests: {counts['integration']}")
    messages.append(f"  Total tests: {counts['total']}")
    
    return success, "\n".join(messages)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_test_count.py <report_file> [expected_count] [tolerance]")
        sys.exit(1)
    
    report_file = sys.argv[1]
    expected_count = int(sys.argv[2]) if len(sys.argv) > 2 else 157
    tolerance = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    print(f"Verifying test count from: {report_file}")
    print(f"Expected unit tests (not slow): {expected_count}±{tolerance}")
    print("-" * 50)
    
    # Load report
    report = load_test_report(report_file)
    if not report:
        sys.exit(1)
    
    # Count tests
    counts = count_tests_by_markers(report)
    if not counts:
        sys.exit(1)
    
    # Verify counts
    success, message = verify_test_count(counts, expected_count, tolerance)
    print(message)
    
    if success:
        print("\n✓ Test count verification PASSED")
        sys.exit(0)
    else:
        print("\n✗ Test count verification FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main() 