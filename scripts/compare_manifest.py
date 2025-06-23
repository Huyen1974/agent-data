#!/usr/bin/env python3
"""
Compare collected.txt vs tests/manifest_519.txt for test synchronization.
Pure Python implementation to avoid Linux-only process substitution.
"""
import sys
import os

def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/compare_manifest.py <collected_file> <manifest_file>")
        sys.exit(1)
    
    collected_file = sys.argv[1]
    manifest_file = sys.argv[2]
    
    # Read collected tests (filter only lines starting with tests/)
    collected_tests = set()
    if os.path.exists(collected_file):
        with open(collected_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('tests/'):
                    collected_tests.add(line)
    
    # Read manifest tests
    manifest_tests = set()
    if os.path.exists(manifest_file):
        with open(manifest_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    manifest_tests.add(line)
    
    # Calculate differences
    missing = manifest_tests - collected_tests  # In manifest but not collected
    extra = collected_tests - manifest_tests    # Collected but not in manifest
    
    # Report results
    print(f"Collection: {len(collected_tests)} tests")
    print(f"Manifest: {len(manifest_tests)} tests")
    print(f"Missing: {len(missing)} tests")
    print(f"Extra: {len(extra)} tests")
    
    if missing:
        print("\nMissing tests (in manifest but not collected):")
        for test in sorted(missing)[:10]:  # Show first 10
            print(f"  {test}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    
    if extra:
        print("\nExtra tests (collected but not in manifest):")
        for test in sorted(extra)[:10]:  # Show first 10
            print(f"  {test}")
        if len(extra) > 10:
            print(f"  ... and {len(extra) - 10} more")
    
    # Return exit code based on differences
    total_diff = len(missing) + len(extra)
    if total_diff == 0:
        print("✅ Perfect sync - manifest matches collection")
        sys.exit(0)
    else:
        print(f"❌ Sync needed - {total_diff} differences found")
        sys.exit(1)

if __name__ == "__main__":
    main() 