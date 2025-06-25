"""
Meta-test to ensure manifest consistency and prevent test drift.
Validates that exactly 106 tests are collected and match manifest_106.txt.
"""

import pytest
import subprocess
import sys
from pathlib import Path


def test_manifest_106_consistency():
    """Ensure pytest collects exactly 106 tests matching manifest_106.txt"""
    
    # Read manifest file
    manifest_path = Path("tests/manifest_106.txt")
    assert manifest_path.exists(), "manifest_106.txt must exist"
    
    with open(manifest_path) as f:
        manifest_tests = set(line.strip() for line in f if line.strip() and not line.startswith("#"))
    
    assert len(manifest_tests) == 106, f"manifest_106.txt should contain exactly 106 tests, found {len(manifest_tests)}"
    
    # Collect actual tests via subprocess to avoid pytest collection hooks interference
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "--collect-only", "--quiet", "--tb=no"
    ], capture_output=True, text=True, cwd=".")
    
    assert result.returncode == 0, f"pytest collection failed: {result.stderr}"
    
    # Extract test nodeids from collection output
    collected_tests = set()
    for line in result.stdout.split('\n'):
        line = line.strip()
        if '::test_' in line and line.startswith('tests/'):
            collected_tests.add(line)
    
    # Verify count
    assert len(collected_tests) == 106, f"Expected 106 tests, collected {len(collected_tests)}"
    
    # Verify sets match exactly
    manifest_not_collected = manifest_tests - collected_tests
    collected_not_manifest = collected_tests - manifest_tests
    
    error_msgs = []
    if manifest_not_collected:
        error_msgs.append(f"Tests in manifest but not collected: {sorted(list(manifest_not_collected)[:5])}...")
    if collected_not_manifest:
        error_msgs.append(f"Tests collected but not in manifest: {sorted(list(collected_not_manifest)[:5])}...")
    
    assert not error_msgs, "\n".join(error_msgs)


def test_no_stray_conftest_files():
    """Ensure no unexpected conftest.py files interfere with collection"""
    
    conftest_files = list(Path(".").rglob("conftest.py"))
    
    # Expected conftest locations (root only for our setup)
    expected_locations = {Path("conftest.py")}
    
    unexpected = [f for f in conftest_files if f not in expected_locations]
    
    # Allow backup files but warn about them
    backup_files = [f for f in unexpected if "backup" in str(f) or "old" in str(f)]
    actual_unexpected = [f for f in unexpected if f not in backup_files]
    
    assert not actual_unexpected, f"Unexpected conftest.py files: {actual_unexpected}"


def test_count_exactly_106():
    """Direct count verification - must be exactly 106"""
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "--collect-only", "-q"
    ], capture_output=True, text=True)
    
    # Count test collection lines (excluding summary lines)
    test_lines = [line for line in result.stdout.split('\n') 
                  if line.strip() and '::test_' in line]
    
    assert len(test_lines) == 106, f"Must collect exactly 106 tests, got {len(test_lines)}"


def test_ci_environment_consistency():
    """Test that would help diagnose CI vs local differences"""
    
    import os
    
    # Log environment for CI debugging
    print(f"Python version: {sys.version}")
    print(f"Working directory: {Path.cwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # This always passes but logs useful info
    assert True 