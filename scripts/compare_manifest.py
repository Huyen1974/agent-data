#!/usr/bin/env python3
"""
G02g: Test manifest comparison script.
Compares current test collection with the locked manifest to ensure consistency.
"""
import sys
import os


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/compare_manifest.py <collected_tests.txt> <manifest_519.txt>")
        sys.exit(1)
    
    collected_file = sys.argv[1]
    manifest_file = sys.argv[2]
    
    # Read collected tests
    try:
        with open(collected_file, 'r') as f:
            collected_tests = set(line.strip() for line in f if line.strip() and '::test_' in line)
    except FileNotFoundError:
        print(f"ERROR: Collected tests file not found: {collected_file}")
        sys.exit(1)
    
    # Read manifest
    try:
        with open(manifest_file, 'r') as f:
            manifest_tests = set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print(f"ERROR: Manifest file not found: {manifest_file}")
        sys.exit(1)
    
    # Compare
    collected_count = len(collected_tests)
    manifest_count = len(manifest_tests)
    
    print(f"Collected tests: {collected_count}")
    print(f"Manifest tests: {manifest_count}")
    
    if collected_count != manifest_count:
        print(f"ERROR: Test count mismatch! Expected {manifest_count}, got {collected_count}")
        
        missing = manifest_tests - collected_tests
        extra = collected_tests - manifest_tests
        
        if missing:
            print(f"\nMissing tests ({len(missing)}):")
            for test in sorted(missing)[:10]:  # Show first 10
                print(f"  - {test}")
            if len(missing) > 10:
                print(f"  ... and {len(missing) - 10} more")
        
        if extra:
            print(f"\nExtra tests ({len(extra)}):")
            for test in sorted(extra)[:10]:  # Show first 10  
                print(f"  + {test}")
            if len(extra) > 10:
                print(f"  ... and {len(extra) - 10} more")
        
        sys.exit(1)
    
    print("✅ Test collection matches manifest!")
    sys.exit(0)


if __name__ == "__main__":
    main() 