"""
Test CLI140e.3.23 validation - nightly.yml merge completion

This test validates that CLI140e.3.23 successfully merged nightly.yml
from cli103a to test branch and maintains proper test count verification.
"""

import os
import pytest


def test_nightly_yml_exists():
    """Test that nightly.yml exists after merge from cli103a"""
    nightly_yml_path = ".github/workflows/nightly.yml"
    assert os.path.exists(nightly_yml_path), "nightly.yml not found after merge"
    
    # Verify content contains test count verification
    with open(nightly_yml_path, "r") as f:
        content = f.read()
        assert "467" in content, "Test count 467 verification missing from nightly.yml"
        assert "pytest --collect-only" in content, "Test collection command missing"
        assert "Verify test count" in content, "Test count verification step missing"


def test_cli140e3_23_completion_marker():
    """Test that CLI140e.3.23 completion is properly tracked"""
    # This test validates the completion of CLI140e.3.23
    # by checking that nightly.yml is available for GitHub Actions CI
    assert os.path.exists(".github/workflows/nightly.yml")
    
    # Verify the workflow can be executed (basic syntax check)
    with open(".github/workflows/nightly.yml", "r") as f:
        content = f.read()
        # Basic YAML workflow structure checks
        assert "name:" in content
        assert "on:" in content
        assert "jobs:" in content


@pytest.mark.meta
def test_cli140e3_23_meta_validation():
    """Meta test for CLI140e.3.23 completion tracking"""
    # This meta test tracks the successful completion of CLI140e.3.23
    completion_markers = [
        ".github/workflows/nightly.yml",  # Main deliverable
    ]
    
    for marker in completion_markers:
        assert os.path.exists(marker), f"CLI140e.3.23 completion marker missing: {marker}" 