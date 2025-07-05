import pytest
import time
import concurrent.futures
from tools.delay_tool import delay_tool


    @pytest.mark.unit
    def test_parallel_calls_under_threshold():
    """Test that parallel calls execute concurrently, not sequentially."""
    num_calls = 3  # Reduced for faster testing
    params = {"delay": 0.2}  # Shorter delay for testing
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_calls) as executor:
        futures = [executor.submit(delay_tool, params) for _ in range(num_calls)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    duration = time.time() - start_time
    # Should complete in ~0.2s (parallel) not ~0.6s (sequential)
    assert duration <= 0.5, f"Expected parallel calls to complete in <= 0.5s, got {duration}s"
    assert all(result["status"] == "success" for result in results), "Expected all calls to succeed"
    assert all(result["delay_applied"] == 0.2 for result in results), "Expected 0.2s delay per call"


@pytest.mark.slow
    @pytest.mark.unit
    def test_parallel_calls_original_timing():
    """Original test with longer delays - marked as slow."""
    num_calls = 5
    params = {"delay": 1.0}  # Each call delays 1s
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_calls) as executor:
        futures = [executor.submit(delay_tool, params) for _ in range(num_calls)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    duration = time.time() - start_time
    assert duration <= 3.0, f"Expected parallel calls to complete in <= 3s, got {duration}s"
    assert all(result["status"] == "success" for result in results), "Expected all calls to succeed"
    assert all(result["delay_applied"] == 1.0 for result in results), "Expected 1s delay per call"
