#!/usr/bin/env python3
"""
Check skipped test count from pytest output.
Usage: python scripts/check_skipped.py <pytest_output_file> <max_skipped>
"""
import sys
from pathlib import Path

def main():
    """Check skipped test count from pytest output file."""
    if len(sys.argv) != 3:
        print("Usage: python scripts/check_skipped.py <pytest_output_file> <max_skipped>")
        sys.exit(1)
    
    output_file = Path(sys.argv[1])
    max_skipped = int(sys.argv[2])
    
    if not output_file.exists():
        print(f"❌ Output file not found: {output_file}")
        sys.exit(1)
    
    skipped_count = 0
    with open(output_file, 'r') as f:
        for line in f:
            if "SKIPPED" in line.upper():
                skipped_count += 1
    
    print(f"📊 Found {skipped_count} skipped tests")
    
    if skipped_count <= max_skipped:
        print(f"✅ Skipped count: {skipped_count} (within limit of {max_skipped})")
        return 0
    else:
        print(f"❌ Too many skipped tests: {skipped_count} > {max_skipped}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 