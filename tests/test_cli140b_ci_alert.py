# tests/test_cli140b_ci_alert.py
# CLI 140b: Nightly CI Runtime and Alerting Policy Validation
#
# This test validates:
# 1. Alerting policy files exist and are properly formatted
# 2. CI runtime expectations are documented
# 3. Alerting policy deployment readiness
#
# Following the "1 test per CLI" rule - this is the single test for CLI 140b

import json
import pytest
from pathlib import Path


@pytest.mark.observability
    @pytest.mark.unitdef test_cli140b_alerting_policies_and_ci_validation():
    """
    CLI 140b: Validates alerting policy files exist and CI runtime documentation.

    This test ensures:
    - CSKH latency alerting policy exists with >1s threshold
    - Error rate alerting policy exists with >5% threshold
    - Alerting policies are properly formatted JSON
    - CI runtime expectations are documented
    - Test count updated to 365 (133 active, 232 deferred)
    """
    # Validate alerting policy files exist
    project_root = Path(__file__).parent.parent

    cskh_latency_policy = project_root / "alert_policy_cskh_latency.json"
    error_rate_policy = project_root / "alert_policy_error_rate.json"

    assert cskh_latency_policy.exists(), "CSKH latency alerting policy file must exist"
    assert error_rate_policy.exists(), "Error rate alerting policy file must exist"

    # Validate CSKH latency policy content
    with open(cskh_latency_policy, "r") as f:
        cskh_policy = json.load(f)

    assert cskh_policy["displayName"] == "CSKH Agent API Latency Alert"
    assert cskh_policy["enabled"] is True
    assert len(cskh_policy["conditions"]) >= 3  # CSKH, RAG, A2A latency conditions

    # Verify latency threshold is >1s (1.0 seconds)
    latency_conditions = [c for c in cskh_policy["conditions"] if "Latency High" in c["displayName"]]
    assert len(latency_conditions) >= 3, "Should have CSKH, RAG, and A2A latency conditions"

    for condition in latency_conditions:
        threshold = condition["conditionThreshold"]["thresholdValue"]
        assert threshold == 1.0, f"Latency threshold should be 1.0s, got {threshold}"
        assert condition["conditionThreshold"]["comparison"] == "COMPARISON_GT"

    # Validate error rate policy content
    with open(error_rate_policy, "r") as f:
        error_policy = json.load(f)

    assert error_policy["displayName"] == "Agent Data API Error Rate Alert"
    assert error_policy["enabled"] is True
    assert len(error_policy["conditions"]) >= 4  # CSKH, A2A, RAG, Qdrant error conditions

    # Verify error rate threshold is >5% (0.05)
    error_conditions = [c for c in error_policy["conditions"] if "Error Rate High" in c["displayName"]]
    assert len(error_conditions) >= 4, "Should have CSKH, A2A, RAG, and Qdrant error rate conditions"

    for condition in error_conditions:
        threshold = condition["conditionThreshold"]["thresholdValue"]
        assert threshold == 0.05, f"Error rate threshold should be 0.05 (5%), got {threshold}"
        assert condition["conditionThreshold"]["comparison"] == "COMPARISON_GT"

    # Validate CI runtime documentation exists
    cli140_guide = project_root / ".cursor" / "CLI140_guide.txt"
    assert cli140_guide.exists(), "CLI140 guide must exist for CI runtime documentation"

    # Validate test count remains controlled (364 tests total)
    # This ensures we're following the selective test execution strategy
    with open(cli140_guide, "r") as f:
        guide_content = f.read()

    # Check that test count is documented as 365 (after CLI 140b addition)
    assert "365 tests" in guide_content, "CLI140 guide should document 365 total tests"

    # Validate alerting policy deployment readiness
    # Check that policies have proper structure for gcloud deployment
    required_fields = ["displayName", "conditions", "combiner", "enabled"]

    for policy_name, policy_data in [("CSKH Latency", cskh_policy), ("Error Rate", error_policy)]:
        for field in required_fields:
            assert field in policy_data, f"{policy_name} policy missing required field: {field}"

        # Validate conditions structure
        for i, condition in enumerate(policy_data["conditions"]):
            assert "displayName" in condition, f"{policy_name} condition {i} missing displayName"
            assert "conditionThreshold" in condition, f"{policy_name} condition {i} missing conditionThreshold"

            threshold = condition["conditionThreshold"]
            assert "filter" in threshold, f"{policy_name} condition {i} missing filter"
            assert "comparison" in threshold, f"{policy_name} condition {i} missing comparison"
            assert "thresholdValue" in threshold, f"{policy_name} condition {i} missing thresholdValue"

    # Success: All alerting policies are properly configured and ready for deployment
    # CI runtime validation will be confirmed when nightly workflow is triggered
    assert True, "CLI 140b alerting policies and CI validation completed successfully"
