#!/usr/bin/env python3
"""
Debug script to understand test discovery differences between CI and local
"""

import os
import re
import subprocess
import sys


def run_pytest_with_details():
    """Run pytest with detailed output to understand what's happening."""
    command = [
        "pytest",
        "--collect-only",
        "-m",
        "not slow and not integration and not e2e",
        "-v",
        "--tb=short",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode


def parse_test_count_detailed(output):
    """Parse the test count and show collection details."""
    # Find the summary line
    collected_match = re.search(r"collected (\d+) items", output)
    deselected_match = re.search(r"(\d+) deselected", output)

    collected = int(collected_match.group(1)) if collected_match else 0
    deselected = int(deselected_match.group(1)) if deselected_match else 0
    active_tests = collected - deselected

    return collected, deselected, active_tests


def check_import_errors(stderr):
    """Check for import errors or other collection issues."""
    import_errors = []
    if "ImportError" in stderr:
        lines = stderr.split("\n")
        for i, line in enumerate(lines):
            if "ImportError" in line:
                import_errors.append(line)
                # Get context
                if i > 0:
                    import_errors.append(f"  Context: {lines[i-1]}")
                if i < len(lines) - 1:
                    import_errors.append(f"  Context: {lines[i+1]}")
    return import_errors


def main():
    print("🔍 Debugging test discovery...")
    print(f"📁 Current directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path}")

    # Show environment
    print("\n📊 Environment Info:")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")

    # Check if we're in CI
    is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
    print(f"🏗️ Running in CI: {is_ci}")

    # Run test discovery
    print("\n🔍 Running test discovery...")
    stdout, stderr, returncode = run_pytest_with_details()

    print(f"Return code: {returncode}")

    if stderr:
        print("\n⚠️ STDERR output:")
        print(stderr)

        # Check for import errors
        import_errors = check_import_errors(stderr)
        if import_errors:
            print("\n❌ Import errors found:")
            for error in import_errors:
                print(f"  {error}")

    if stdout:
        print("\n📝 Test discovery output (last 50 lines):")
        lines = stdout.split("\n")
        for line in lines[-50:]:
            if line.strip():
                print(f"  {line}")

    # Parse counts
    if stdout:
        collected, deselected, active_tests = parse_test_count_detailed(stdout)
        print("\n📊 Test Count Summary:")
        print(f"  Total collected: {collected}")
        print(f"  Deselected: {deselected}")
        print(f"  Active tests: {active_tests}")

        # Check against expected
        expected = 856
        if active_tests < expected:
            print(f"❌ Missing {expected - active_tests} tests from expected count")
        elif active_tests > expected:
            print(f"⚠️ Found {active_tests - expected} more tests than expected")
        else:
            print(f"✅ Test count matches expected: {active_tests}")

        return active_tests == expected

    return False


if __name__ == "__main__":
    success = main()
    print(f"\n🏁 Debug complete. Success: {success}")
    sys.exit(0 if success else 1)
