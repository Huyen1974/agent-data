#!/usr/bin/env python3
"""
Build manifest_ci.txt with exactly 519 tests for G02h recovery.
"""
import os
import sys
from pathlib import Path

def main():
    """Build tests/manifest_ci.txt from tests/manifest_519.txt"""
    
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Source and target manifest files
    source_manifest = project_root / "tests" / "manifest_519.txt"
    target_manifest = project_root / "tests" / "manifest_ci.txt"
    
    if not source_manifest.exists():
        print(f"❌ Source manifest not found: {source_manifest}")
        sys.exit(1)
    
    # Read and validate source manifest
    with open(source_manifest, 'r') as f:
        tests = [line.strip() for line in f if line.strip()]
    
    if len(tests) != 519:
        print(f"❌ Expected 519 tests in source manifest, found {len(tests)}")
        sys.exit(1)
    
    # Sort tests for consistency
    tests.sort()
    
    # Write target manifest
    with open(target_manifest, 'w') as f:
        for test in tests:
            f.write(f"{test}\n")
    
    print(f"✅ Built {target_manifest} with {len(tests)} tests")
    print(f"📊 Source: {source_manifest}")
    print(f"📊 Target: {target_manifest}")
    
    # Validate written manifest
    with open(target_manifest, 'r') as f:
        written_tests = [line.strip() for line in f if line.strip()]
    
    if len(written_tests) != 519:
        print(f"❌ Validation failed: wrote {len(written_tests)} tests, expected 519")
        sys.exit(1)
    
    print(f"✅ Validation passed: {len(written_tests)} tests written")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 