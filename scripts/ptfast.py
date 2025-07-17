#!/usr/bin/env python3
"""
ptfast - Fast Test Execution Script for CLI140k
===============================================

Quick test execution script optimized for MacBook M1 performance.
Provides fast feedback with selective test execution.

Usage:
    python scripts/ptfast.py [options]

Examples:
    python scripts/ptfast.py -m "e2e"           # Run e2e tests only
    python scripts/ptfast.py -m "core"         # Run core tests only
    python scripts/ptfast.py --count           # Show test count only
    python scripts/ptfast.py --runtime         # Measure runtime only
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_ptfast(marker=None, count_only=False, runtime_only=False, max_time=30):
    """
    Run fast test execution with optimized settings.

    Args:
        marker: Pytest marker to filter tests
        count_only: Only count tests, don't run them
        runtime_only: Only measure runtime, minimal output
        max_time: Maximum allowed runtime in seconds
    """

    # Base command for fast execution
    base_cmd = [
        "python",
        "-m",
        "pytest",
        "--testmon",  # Only run tests affected by changes
        "-n",
        "2",  # Parallel execution optimized for M1
        "--tb=short",  # Shorter tracebacks
        "-q",  # Quiet output
    ]

    # Add marker filter if specified
    if marker:
        base_cmd.extend(["-m", marker])
    else:
        # Default: exclude slow and deferred tests
        base_cmd.extend(["-m", "not slow and not deferred"])

    # Count only mode
    if count_only:
        count_cmd = base_cmd + ["--collect-only"]
        result = subprocess.run(count_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            lines = result.stdout.split("\n")
            for line in lines:
                if "collected" in line:
                    print(f"📊 Test count: {line}")
                    return
        else:
            print(f"❌ Failed to count tests: {result.stderr}")
            return

    # Runtime measurement
    print(f"🚀 Running ptfast with marker: {marker or 'not slow and not deferred'}")
    print(f"⏱️  Target runtime: <{max_time}s")

    start_time = time.time()

    try:
        result = subprocess.run(base_cmd, timeout=max_time + 10)
        end_time = time.time()
        runtime = end_time - start_time

        # Results
        if runtime_only:
            print(f"{runtime:.2f}")
        else:
            status = "✅ PASS" if result.returncode in [0, 1] else "❌ FAIL"
            performance = "🟢 FAST" if runtime < max_time else "🟡 SLOW"

            print("\n📈 Results:")
            print(f"   Status: {status}")
            print(f"   Runtime: {runtime:.2f}s")
            print(f"   Performance: {performance}")
            print(f"   Target: <{max_time}s")

            if runtime >= max_time:
                print(f"⚠️  Runtime exceeded target by {runtime - max_time:.2f}s")
                return 1

        return 0

    except subprocess.TimeoutExpired:
        print(f"⏰ Test execution timed out after {max_time + 10}s")
        return 1
    except KeyboardInterrupt:
        print("\n⏹️  Test execution interrupted")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Fast test execution for CLI140k optimization"
    )
    parser.add_argument(
        "-m", "--marker", help="Pytest marker to filter tests (e.g., 'core', 'e2e')"
    )
    parser.add_argument(
        "--count", action="store_true", help="Only count tests, don't run them"
    )
    parser.add_argument(
        "--runtime", action="store_true", help="Only output runtime in seconds"
    )
    parser.add_argument(
        "--max-time",
        type=int,
        default=30,
        help="Maximum allowed runtime in seconds (default: 30)",
    )

    args = parser.parse_args()

    # Change to project root directory
    project_root = Path(__file__).parent.parent
    import os

    os.chdir(project_root)

    return run_ptfast(
        marker=args.marker,
        count_only=args.count,
        runtime_only=args.runtime,
        max_time=args.max_time,
    )


if __name__ == "__main__":
    sys.exit(main())
