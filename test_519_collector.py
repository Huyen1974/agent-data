#!/usr/bin/env python3
"""Test collection script that enforces exactly 519 tests from manifest."""

import subprocess
import sys
import pathlib
import time


def load_manifest():
    """Load the manifest file."""
    manifest_file = pathlib.Path("/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/tests/manifest_519.txt")
    
    if not manifest_file.exists():
        print(f"ERROR: manifest_519.txt not found at {manifest_file}")
        sys.exit(1)
    
    manifest_nodeids = set()
    with open(manifest_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                manifest_nodeids.add(line)
    
    if len(manifest_nodeids) != 519:
        print(f"ERROR: Manifest contains {len(manifest_nodeids)} tests, expected 519")
        sys.exit(1)
    
    return manifest_nodeids


def collect_tests():
    """Collect all available tests."""
    print(">>> Collecting all tests...")
    result = subprocess.run([
        'pytest', '--collect-only', '-q', '--qdrant-mock', '--tb=no'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"ERROR: pytest collection failed: {result.stderr}")
        sys.exit(1)
    
    # Parse collected tests
    collected_tests = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and '::' in line and not line.startswith('='):
            collected_tests.append(line)
    
    return collected_tests


def main():
    """Main function."""
    start_time = time.time()
    
    print("=== g2y-fix-fixtures-4: Enforcing 519 test collection ===")
    
    # Load manifest
    manifest_nodeids = load_manifest()
    print(f">>> Loaded {len(manifest_nodeids)} tests from manifest")
    
    # Collect available tests
    collected_tests = collect_tests()
    print(f">>> Found {len(collected_tests)} tests in collection")
    
    # Filter to manifest tests only
    filtered_tests = []
    for test in collected_tests:
        if test in manifest_nodeids:
            filtered_tests.append(test)
    
    # Verify exactly 519 tests
    final_count = len(filtered_tests)
    
    if final_count != 519:
        print(f">>> FATAL: Expected exactly 519 tests, got {final_count}")
        
        # Show diagnostics
        collected_set = set(collected_tests)
        missing = manifest_nodeids - collected_set
        extra = collected_set - manifest_nodeids
        
        if missing:
            print(f">>> Missing {len(missing)} tests from collection (first 10):")
            for test in sorted(missing)[:10]:
                print(f">>>   - {test}")
        
        if extra:
            print(f">>> Extra {len(extra)} tests not in manifest (first 10):")
            for test in sorted(extra)[:10]:
                print(f">>>   + {test}")
        
        sys.exit(1)
    
    elapsed = time.time() - start_time
    print(f">>> ✅ SUCCESS: Exactly 519 tests collected in {elapsed:.1f}s!")
    print(f"519")  # Output for wc -l


if __name__ == "__main__":
    main() 