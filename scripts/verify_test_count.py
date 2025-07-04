#!/usr/bin/env python3
"""
Test Count Verification Script for CLI145
Validates that test count is within expected range (~157 ± 10)
"""
import json
import sys
import os
import argparse

def verify_test_count(report_file='.report.json', expected_count=157, tolerance=10):
    """
    Verify test count from pytest JSON report.
    
    Args:
        report_file: Path to pytest JSON report file
        expected_count: Expected number of tests
        tolerance: Allowed deviation from expected count
    
    Returns:
        bool: True if test count is within acceptable range
    """
    try:
        if not os.path.exists(report_file):
            print(f"ERROR: Report file {report_file} not found")
            return False
            
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        summary = report['summary']
        # For collection-only runs, use collected - deselected to get selected count
        if 'collected' in summary and 'deselected' in summary:
            total = summary['collected'] - summary['deselected']
            print(f"Total tests collected: {summary['collected']}")
            print(f"Deselected tests: {summary['deselected']}")
            print(f"Selected tests: {total}")
        else:
            # For actual test runs, use total
            total = summary['total']
            print(f"Total tests executed: {total}")
        
        min_expected = expected_count - tolerance
        max_expected = expected_count + tolerance
        
        print(f"Expected range: {min_expected} - {max_expected}")
        
        if min_expected <= total <= max_expected:
            print(f"✅ SUCCESS: Test count {total} is within expected range")
            return True
        else:
            print(f"❌ FAILURE: Test count {total} is outside expected range")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to verify test count: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify pytest test count from JSON report")
    parser.add_argument("report_file", nargs="?", default=".report.json", 
                        help="Path to pytest JSON report file (default: .report.json)")
    parser.add_argument("expected_count", nargs="?", type=int, default=157,
                        help="Expected number of tests (default: 157)")
    parser.add_argument("tolerance", nargs="?", type=int, default=10,
                        help="Allowed deviation from expected count (default: 10)")
    
    args = parser.parse_args()
    success = verify_test_count(args.report_file, args.expected_count, args.tolerance)
    sys.exit(0 if success else 1) 