import time
from tools.delay_tool import delay_tool
import pytest


@pytest.mark.deferred
def test_delay_tool_completes_under_2s():
    """Test that delay tool caps delays at 2 seconds maximum."""
    params = {"delay": 3.0}  # Request > 2s to test cap
    start_time = time.time()
    result = delay_tool(params)
    duration = time.time() - start_time

    assert duration <= 2.1, f"Expected delay <= 2s, got {duration}s"
    assert result["status"] == "success", "Expected success status"
    assert result["delay_applied"] == 2.0, "Expected delay capped at 2s"


@pytest.mark.deferred
def test_delay_tool_short_delay():
    """Test delay tool with a short delay for faster testing."""
    params = {"delay": 0.1}  # Short delay for testing
    start_time = time.time()
    result = delay_tool(params)
    duration = time.time() - start_time

    assert duration <= 0.2, f"Expected delay <= 0.2s, got {duration}s"
    assert result["status"] == "success", "Expected success status"
    assert result["delay_applied"] == 0.1, "Expected 0.1s delay"
