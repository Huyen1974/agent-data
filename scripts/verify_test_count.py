#!/usr/bin/env python3
"""
Test Count Verification Script for CLI 182.5
Verifies that the test count is stable around 932 tests for 'pytest --json-report --json-report-file=.report.json --collect-only -q'
"""

import json
import sys
import os
from pathlib import Path

def verify_test_count():
    """Verify test count from pytest json report"""
    report_file = Path(".report.json")
    
    if not report_file.exists():
        print(f"❌ ERROR: Report file {report_file} not found!")
        print("Run pytest with --json-report --json-report-file=.report.json first")
        sys.exit(1)
    
    try:
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        # Extract test count information from collection
        summary = report.get('summary', {})
        collected_tests = summary.get('collected', 0)  # Use 'collected' for --collect-only
        total_tests = summary.get('total', 0)  # This will be 0 for collect-only runs
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        skipped = summary.get('skipped', 0)
        errors = summary.get('error', 0)
        
        # Expected range for stable test count (around 932)
        target_count = 932
        variance_percent = 5
        variance = int(target_count * variance_percent / 100)
        expected_min = target_count - variance  # 885
        expected_max = target_count + variance  # 979
        
        print(f"📊 Test Count Verification Report")
        print(f"=" * 50)
        print(f"Collected Tests: {collected_tests}")
        print(f"Total Tests Executed: {total_tests}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Skipped: {skipped}")
        print(f"Errors: {errors}")
        print(f"Expected Range: {expected_min}-{expected_max}")
        print(f"Target Count: {target_count}")
        print(f"=" * 50)
        
        # Use collected_tests as the primary metric for --collect-only runs
        test_count = collected_tests if collected_tests > 0 else total_tests
        
        # Verify test count is in expected range
        if expected_min <= test_count <= expected_max:
            deviation = abs(test_count - target_count)
            if deviation <= 10:
                print(f"✅ SUCCESS: Test count {test_count} is within acceptable range!")
                print(f"   Deviation from target: {deviation} tests")
                return True
            else:
                print(f"⚠️  WARNING: Test count {test_count} is in range but deviates from target by {deviation}")
                print(f"   This is acceptable but should be monitored")
                return True
        else:
            print(f"❌ FAILURE: Test count {test_count} is outside expected range ({expected_min}-{expected_max})")
            print(f"   This indicates test count instability")
            return False
            
    except json.JSONDecodeError:
        print(f"❌ ERROR: Invalid JSON in {report_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to read report: {e}")
        sys.exit(1)

def main():
    """Main verification function"""
    print("🧪 Agent Data Test Count Verification - CLI 182.5")
    print(f"Timestamp: {os.popen('date').read().strip()}")
    
    success = verify_test_count()
    
    if success:
        print("\n🎉 Test count verification PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Test count verification FAILED!")
        print("Please check test markers and configuration")
        sys.exit(1)

if __name__ == "__main__":
    main() 