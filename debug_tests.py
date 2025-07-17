#!/usr/bin/env python3
"""
Debug script to count active and deferred tests.
Used by CLI126C test validation.
"""

import subprocess
import sys


def count_tests():
    """Count active and deferred tests."""
    try:
        # Count active tests (not slow and not deferred)
        active_result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-m",
                "not slow and not deferred",
            ],
            capture_output=True,
            text=True,
        )

        active_lines = [
            line for line in active_result.stdout.split("\n") if "::test_" in line
        ]
        active_count = len(active_lines)

        # Count deferred tests
        deferred_result = subprocess.run(
            ["python", "-m", "pytest", "--collect-only", "-q", "-m", "deferred"],
            capture_output=True,
            text=True,
        )

        deferred_lines = [
            line for line in deferred_result.stdout.split("\n") if "::test_" in line
        ]
        deferred_count = len(deferred_lines)

        # Output in expected format
        print(f"Active tests: {active_count}")
        print(f"Deferred tests: {deferred_count}")
        print(f"Total tests analyzed: {active_count + deferred_count}")

        return 0

    except Exception as e:
        print(f"Error counting tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(count_tests())
