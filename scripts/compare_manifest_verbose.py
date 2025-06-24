#!/usr/bin/env python3
"""
Compare collected test list with manifest_ci.txt for G02h recovery.
Show ALL differences, not just first 10.
"""
import sys
from pathlib import Path

def normalize_test_name(test_line):
    """Normalize a test name from pytest collection output."""
    # Handle pytest collection output format
    if "::" in test_line:
        return test_line.strip()
    # Handle raw lines
    return test_line.strip()

def read_collected_tests(collected_file):
    """Read tests from pytest --collect-only output."""
    collected_path = Path(collected_file)
    if not collected_path.exists():
        print(f"❌ Collected tests file not found: {collected_file}")
        return None
    
    tests = []
    with open(collected_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and "::" in line and not line.startswith("="):
                # This is a test line
                tests.append(normalize_test_name(line))
    
    return sorted(tests)

def read_manifest_tests(manifest_file):
    """Read tests from manifest file."""
    manifest_path = Path(manifest_file)
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_file}")
        return None
    
    tests = []
    with open(manifest_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                tests.append(normalize_test_name(line))
    
    return sorted(tests)

def compare_test_sets(collected_tests, manifest_tests):
    """Compare two sets of tests and report differences."""
    collected_set = set(collected_tests)
    manifest_set = set(manifest_tests)
    
    # Tests in manifest but not collected
    missing_from_collected = manifest_set - collected_set
    
    # Tests collected but not in manifest  
    extra_in_collected = collected_set - manifest_set
    
    return missing_from_collected, extra_in_collected

def main():
    """Compare collected tests with manifest and show ALL differences."""
    if len(sys.argv) != 3:
        print("Usage: python compare_manifest_verbose.py <collected_file> <manifest_file>")
        sys.exit(1)
    
    collected_file = sys.argv[1]
    manifest_file = sys.argv[2]
    
    # Read test lists
    collected_tests = read_collected_tests(collected_file)
    manifest_tests = read_manifest_tests(manifest_file)
    
    if collected_tests is None or manifest_tests is None:
        print("❌ Failed to read test files")
        sys.exit(1)
    
    print(f"📊 Collected tests: {len(collected_tests)}")
    print(f"📊 Manifest tests: {len(manifest_tests)}")
    
    # Compare test sets
    missing, extra = compare_test_sets(collected_tests, manifest_tests)
    
    if len(collected_tests) != len(manifest_tests):
        print(f"❌ Test count mismatch: collected {len(collected_tests)}, manifest {len(manifest_tests)}")
    
    if missing:
        print(f"❌ Missing from collected ({len(missing)} tests):")
        for test in sorted(missing):
            print(f"   - {test}")
    
    if extra:
        print(f"❌ Extra in collected ({len(extra)} tests):")
        for test in sorted(extra):
            print(f"   + {test}")
    
    # Final verdict
    if not missing and not extra and len(collected_tests) == len(manifest_tests):
        print("✅ Test collection matches manifest perfectly!")
        return 0
    else:
        print("❌ Test collection does not match manifest")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 