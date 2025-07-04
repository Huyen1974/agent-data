#!/usr/bin/env python3
"""
Test Count Verification Script for CLI145
Validates that test count is within expected range (~157 ± 10)
"""
import json
import sys
import os

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
        
        total = report['summary']['total']
        min_expected = expected_count - tolerance
        max_expected = expected_count + tolerance
        
        print(f"Total tests collected: {total}")
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
    success = verify_test_count()
    sys.exit(0 if success else 1) 