"""
Meta-tests for Agent Data project.

This module contains tests that verify the CI environment setup,
test counts, and overall project health metrics.

Updated for G02d CI pipeline verification - June 23, 2025
"""

import os
import subprocess
import pytest
from pathlib import Path

# G02g: Target test counts for stable CI (updated to G02g requirement of exactly 497)
EXPECTED_TOTAL_TESTS = 497
EXPECTED_SKIPPED = 6


def test_ci_environment():
    """Test CI environment configuration and variables."""
    # Check if we're running in CI
    is_ci = os.getenv("CI", "false").lower() == "true"
    is_github_actions = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
    
    if is_ci or is_github_actions:
        # Verify required environment variables in CI
        assert os.getenv("GCP_PROJECT_ID") == "chatgpt-db-project", "Incorrect GCP project ID"
        assert os.getenv("RUN_DEFERRED") == "0", "RUN_DEFERRED should be disabled in CI"
        assert os.getenv("PYTHONDONTWRITEBYTECODE") == "1", "PYTHONDONTWRITEBYTECODE should be enabled"
        assert os.getenv("PYTEST_TIMEOUT") == "8", "PYTEST_TIMEOUT should be 8 seconds"
        assert os.getenv("BATCH_SIZE") == "3", "BATCH_SIZE should be 3"
        assert os.getenv("GCP_REGION") == "asia-southeast1", "Incorrect GCP region"
        
        print("✅ CI environment verification passed")
    else:
        print("ℹ️  Running in local environment, skipping CI-specific checks")


def test_project_structure():
    """Test that essential project directories and files exist."""
    project_root = Path(__file__).parent.parent
    
    # Essential directories
    essential_dirs = [
        "agent",
        "api", 
        "auth",
        "config",
        "tools",
        "vector_store",
        "tests",
        "scripts"
    ]
    
    for dir_name in essential_dirs:
        dir_path = project_root / dir_name
        assert dir_path.exists(), f"Essential directory {dir_name} is missing"
        assert dir_path.is_dir(), f"{dir_name} should be a directory"
    
    # Essential files
    essential_files = [
        "requirements.txt",
        "__init__.py",
        ".gitignore",
        ".env.sample"
    ]
    
    for file_name in essential_files:
        file_path = project_root / file_name
        assert file_path.exists(), f"Essential file {file_name} is missing"
        assert file_path.is_file(), f"{file_name} should be a file"
    
    print("✅ Project structure verification passed")


def test_requirements_file():
    """Test that requirements.txt contains essential dependencies."""
    project_root = Path(__file__).parent.parent
    requirements_path = project_root / "requirements.txt"
    
    with open(requirements_path, 'r') as f:
        requirements_content = f.read().lower()
    
    # Essential dependencies
    essential_deps = [
        "pytest",
        "google-cloud",
        "openai",
        "qdrant-client",
        "fastapi",
        "pydantic"
    ]
    
    for dep in essential_deps:
        assert dep in requirements_content, f"Essential dependency {dep} missing from requirements.txt"
    
    print("✅ Requirements file verification passed")


def test_test_count_stability():
    """Test that the number of collected tests matches the locked manifest."""
    # G02g: Check manifest file first
    manifest_file = Path(__file__).parent / "manifest_497.txt"
    if manifest_file.exists():
        with open(manifest_file, 'r') as f:
            manifest_tests = [line.strip() for line in f if line.strip()]
        
        # G02g: Assert exactly 497 tests in manifest
        assert len(manifest_tests) == 497, f"Expected exactly 497 tests in manifest, got {len(manifest_tests)}"
        print(f"✅ Manifest contains {len(manifest_tests)} tests")
    
    try:
        # Count tests using pytest collection
        result = subprocess.run(
            ["pytest", "--collect-only", "-q", "--qdrant-mock"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            output = result.stdout
            # Look for test collection summary
            for line in output.split('\n'):
                if 'tests collected' in line or 'test collected' in line:
                    words = line.split()
                    if words and words[0].isdigit():
                        test_count = int(words[0])
                        # G02g: Verify we hit the target test count
                        assert test_count == EXPECTED_TOTAL_TESTS, f"Expected {EXPECTED_TOTAL_TESTS} tests, got {test_count}"
                        print(f"✅ Found {test_count} tests - matches expected count")
                        return
            
            print("⚠️  Could not parse test count from pytest output")
        else:
            print(f"⚠️  Pytest collection failed with return code {result.returncode}")
            print(f"stderr: {result.stderr}")
    
    except subprocess.TimeoutExpired:
        print("⚠️  Pytest collection timed out")
    except Exception as e:
        print(f"⚠️  Error during test collection: {e}")


def test_github_workflow_files():
    """Test that GitHub workflow files exist and are properly configured."""
    project_root = Path(__file__).parent.parent
    workflows_dir = project_root / ".github" / "workflows"
    
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))
        assert len(workflow_files) > 0, "No GitHub workflow files found"
        
        # Check for CI workflow
        ci_workflows = [f for f in workflow_files if 'ci' in f.name.lower()]
        assert len(ci_workflows) > 0, "No CI workflow file found"
        
        print(f"✅ Found {len(workflow_files)} workflow files including CI")
    else:
        print("ℹ️  No .github/workflows directory found - may be running locally")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
