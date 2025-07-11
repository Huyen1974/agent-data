import pytest
# tests/api/test_metrics.py
# This file is part of the MPC Back End for Agents project.
#
# This module contains tests for the Prometheus metrics middleware functionality.
# It verifies that the /metrics endpoint is accessible and returns proper Prometheus format.
#
# DEPENDENCIES:
# - fastapi.testclient: For making HTTP requests to the API.
# - pytest: For test framework.
#
# USAGE:
# - This test is run automatically as part of the pytest suite.
# - Tests the /metrics endpoint exposed by the Prometheus middleware.

from fastapi.testclient import TestClient


@pytest.mark.unit
def test_metrics_endpoint(client: TestClient):
    """Test that the /metrics endpoint returns Prometheus metrics in the correct format."""
    # Make a request to the /metrics endpoint
    response = client.get("/metrics")

    # Verify the response status code
    assert response.status_code == 200

    # Verify the content type is text/plain (Prometheus format)
    assert "content-type" in response.headers
    assert response.headers["content-type"].startswith("text/plain")

    # Verify that the response contains expected Prometheus metrics
    response_text = response.text
    assert "api_requests_total" in response_text
    assert "api_request_duration_seconds" in response_text

    # Verify that the metrics follow Prometheus format (basic check)
    # Prometheus metrics should contain lines with metric names and values
    lines = response_text.strip().split("\n")
    metric_lines = [line for line in lines if line and not line.startswith("#")]
    assert len(metric_lines) > 0, "Should contain at least some metric data lines"
