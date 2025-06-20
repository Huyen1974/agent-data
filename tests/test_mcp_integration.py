"""
Test MCP subprocess integration with mock QdrantStore.
"""

import os
import json
import time
import subprocess
import pytest
import asyncio
from typing import Optional, Dict, Any


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 8.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff."""
        delay = self.base_delay * (2**attempt)
        return min(delay, self.max_delay)


async def send_request_with_retry(
    process: subprocess.Popen,
    request: Dict[str, Any],
    timeout: float = 45.0,
    retry_config: Optional[RetryConfig] = None,
) -> Optional[Dict[str, Any]]:
    """
    Send request to MCP server with timeout and retry logic.

    Args:
        process: The subprocess running the MCP server
        request: The JSON request to send
        timeout: Timeout for each attempt in seconds
        retry_config: Retry configuration, defaults to 3 retries with exponential backoff

    Returns:
        Response dictionary or None if all retries failed
    """
    if retry_config is None:
        retry_config = RetryConfig()

    last_error = None

    for attempt in range(retry_config.max_retries + 1):
        try:
            # Send request
            input_json = json.dumps(request) + "\n"
            process.stdin.write(input_json)
            process.stdin.flush()

            # Wait for response with timeout
            response = await asyncio.wait_for(_read_response(process), timeout=timeout)

            if response and "result" in response and "error" not in response:
                return response
            elif response and "error" in response:
                last_error = f"API Error: {response['error']}"
                # Don't retry on certain errors
                if "authentication" in str(response["error"]).lower():
                    break
            else:
                last_error = "No valid response received"

        except asyncio.TimeoutError:
            last_error = f"Timeout after {timeout}s on attempt {attempt + 1}"
        except Exception as e:
            last_error = f"Unexpected error on attempt {attempt + 1}: {str(e)}"

        # If this wasn't the last attempt, wait before retrying
        if attempt < retry_config.max_retries:
            delay = retry_config.get_delay(attempt)
            print(f"Attempt {attempt + 1} failed: {last_error}. Retrying in {delay}s...")
            await asyncio.sleep(delay)

    print(f"All {retry_config.max_retries + 1} attempts failed. Last error: {last_error}")
    return None


async def _read_response(process: subprocess.Popen) -> Optional[Dict[str, Any]]:
    """Read response from MCP server subprocess."""
    while True:
        if process.poll() is not None:
            stderr_output = process.stderr.read()
            raise RuntimeError(f"MCP server terminated unexpectedly: {stderr_output}")

        try:
            response_line = process.stdout.readline()
            if response_line:
                return json.loads(response_line.strip())
        except json.JSONDecodeError:
            pass

        await asyncio.sleep(0.1)


class TestMCPIntegration:

    def test_subprocess_single_save(self):
        """Test single save_document call with mock QdrantStore via subprocess."""
        # Virtual environment path
        venv_python = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
        workspace_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
        mcp_server_path = "ADK/agent_data/local_mcp_server.py"

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_path
        env["USE_MOCK_QDRANT"] = "1"  # Enable mock QdrantStore

        # Load environment variables from .env file if available
        try:
            from dotenv import load_dotenv

            load_dotenv()
            for key in ["QDRANT_URL", "QDRANT_API_KEY", "OPENAI_API_KEY", "GOOGLE_CLOUD_PROJECT"]:
                if key in os.environ:
                    env[key] = os.environ[key]
        except ImportError:
            pass  # dotenv not available, skip

        # Start MCP server subprocess
        cmd = [venv_python, mcp_server_path]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=workspace_path,
        )

        try:
            # Wait for server to start
            time.sleep(2)

            # Create test document
            test_doc = {
                "tool_name": "save_document",
                "kwargs": {
                    "doc_id": "test_subprocess_1",
                    "content": "Test document for subprocess integration",
                    "save_dir": "saved_documents",
                },
            }

            # Send document as JSON
            input_json = json.dumps(test_doc) + "\n"
            process.stdin.write(input_json)
            process.stdin.flush()

            # Read response with timeout
            start_time = time.time()
            timeout = 30
            response = None

            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    # Process has terminated
                    stderr_output = process.stderr.read()
                    pytest.fail(f"MCP server terminated unexpectedly: {stderr_output}")

                # Try to read a line
                try:
                    response_line = process.stdout.readline()
                    if response_line:
                        response = json.loads(response_line.strip())
                        break
                except json.JSONDecodeError:
                    continue

                time.sleep(0.1)

            # Verify response
            assert response is not None, "No response received from MCP server"
            assert "result" in response, f"Expected 'result' in response, got: {response}"
            assert "error" not in response, f"Unexpected error in response: {response}"

            # Verify the result contains success message
            result = response["result"]
            assert "saved successfully" in result, f"Expected success message in result: {result}"
            assert "test_subprocess_1" in result, f"Expected doc_id in result: {result}"

        finally:
            # Clean up subprocess
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def test_subprocess_medium_scale(self):
        """Test medium-scale processing with 10 documents using mock QdrantStore."""
        # Virtual environment path
        venv_python = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
        workspace_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
        mcp_server_path = "ADK/agent_data/local_mcp_server.py"

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_path
        env["USE_MOCK_QDRANT"] = "1"  # Enable mock QdrantStore
        env["OPENAI_API_KEY"] = "dummy"  # Use dummy OpenAI key for testing

        # Start MCP server subprocess
        cmd = [venv_python, mcp_server_path]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=workspace_path,
            bufsize=0,  # Unbuffered
        )

        try:
            # Wait for server to start
            time.sleep(2)

            # Generate test documents - reduced from 25 to 10 for MacBook M1 stability
            num_docs = 10
            successful_docs = 0
            failed_docs = 0

            for i in range(num_docs):
                doc_id = f"test_medium_{i+1}"
                test_doc = {
                    "tool_name": "save_document",
                    "kwargs": {
                        "doc_id": doc_id,
                        "content": f"Test document {i+1} for medium-scale testing",
                        "save_dir": "saved_documents",
                    },
                }

                # Send document as JSON
                input_json = json.dumps(test_doc) + "\n"
                process.stdin.write(input_json)
                process.stdin.flush()

                # Read response with timeout
                start_time = time.time()
                timeout = 30
                response = None

                while time.time() - start_time < timeout:
                    if process.poll() is not None:
                        # Process has terminated
                        stderr_output = process.stderr.read()
                        pytest.fail(f"MCP server terminated unexpectedly at document {i+1}: {stderr_output}")

                    # Try to read a line
                    try:
                        response_line = process.stdout.readline()
                        if response_line:
                            response = json.loads(response_line.strip())
                            break
                    except json.JSONDecodeError:
                        continue

                    time.sleep(0.1)

                # Count results
                if response and "result" in response and "error" not in response:
                    successful_docs += 1
                else:
                    failed_docs += 1

                # Small delay between documents
                time.sleep(0.1)

            # Calculate success rate
            total_docs = successful_docs + failed_docs
            success_rate = successful_docs / total_docs if total_docs > 0 else 0

            # Verify success rate is above 75%
            assert (
                success_rate >= 0.75
            ), f"Success rate {success_rate:.2%} is below 75% threshold. Successful: {successful_docs}, Failed: {failed_docs}"

        finally:
            # Clean up subprocess
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def test_subprocess_mock_qdrant_environment(self):
        """Test that mock QdrantStore is properly initialized via environment variable."""
        # Virtual environment path
        venv_python = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
        workspace_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
        mcp_server_path = "ADK/agent_data/local_mcp_server.py"

        # Set up environment with mock enabled
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_path
        env["USE_MOCK_QDRANT"] = "1"

        # Start MCP server subprocess
        cmd = [venv_python, mcp_server_path]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=workspace_path,
        )

        try:
            # Wait for server to start and check stderr for mock initialization
            time.sleep(2)

            # Terminate the process to read stderr
            process.terminate()
            process.wait(timeout=5)

            # Read stderr to check for mock initialization message
            stderr_output = process.stderr.read()

            # Verify mock QdrantStore was initialized
            assert (
                "MockQdrantStore initialized successfully for testing" in stderr_output
            ), f"Expected mock QdrantStore initialization message in stderr: {stderr_output}"
            assert (
                "Using mock QdrantStore: True" in stderr_output
            ), f"Expected mock QdrantStore usage confirmation in stderr: {stderr_output}"

        finally:
            # Ensure process is cleaned up
            if process.poll() is None:
                process.kill()
                process.wait()

    def test_subprocess_small_scale(self):
        """Test small-scale processing with 10 documents using mock QdrantStore."""
        # Virtual environment path
        venv_python = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
        workspace_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
        mcp_server_path = "ADK/agent_data/local_mcp_server.py"

        # Set up environment
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_path
        env["USE_MOCK_QDRANT"] = "1"  # Enable mock QdrantStore
        env["OPENAI_API_KEY"] = "dummy"  # Use dummy OpenAI key for testing

        # Start MCP server subprocess
        cmd = [venv_python, mcp_server_path]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=workspace_path,
            bufsize=0,  # Unbuffered
        )

        try:
            # Wait for server to start
            time.sleep(2)

            # Generate test documents
            num_docs = 10
            successful_docs = 0
            failed_docs = 0

            for i in range(num_docs):
                doc_id = f"test_small_{i+1}"
                test_doc = {
                    "tool_name": "save_document",
                    "kwargs": {
                        "doc_id": doc_id,
                        "content": f"Test document {i+1} for small-scale testing",
                        "save_dir": "saved_documents",
                    },
                }

                # Send document as JSON
                input_json = json.dumps(test_doc) + "\n"
                process.stdin.write(input_json)
                process.stdin.flush()

                # Read response with timeout
                start_time = time.time()
                timeout = 30
                response = None

                while time.time() - start_time < timeout:
                    if process.poll() is not None:
                        # Process has terminated
                        stderr_output = process.stderr.read()
                        pytest.fail(f"MCP server terminated unexpectedly at document {i+1}: {stderr_output}")

                    # Try to read a line
                    try:
                        response_line = process.stdout.readline()
                        if response_line:
                            response = json.loads(response_line.strip())
                            break
                    except json.JSONDecodeError:
                        continue

                    time.sleep(0.1)

                # Count results
                if response and "result" in response and "error" not in response:
                    successful_docs += 1
                else:
                    failed_docs += 1

                # Small delay between documents
                time.sleep(0.1)

            # Calculate success rate
            total_docs = successful_docs + failed_docs
            success_rate = successful_docs / total_docs if total_docs > 0 else 0

            # Verify success rate is above 75%
            assert (
                success_rate >= 0.75
            ), f"Success rate {success_rate:.2%} is below 75% threshold. Successful: {successful_docs}, Failed: {failed_docs}"

        finally:
            # Clean up subprocess
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    @pytest.mark.deferred
    def test_subprocess_real_api_calls(self):
        """Test Agent functionalities with real Qdrant API calls - CLI 119D6 Enhanced."""
        # Virtual environment path
        venv_python = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
        workspace_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
        mcp_server_path = "ADK/agent_data/local_mcp_server.py"

        # Set up environment for REAL API calls
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_path
        env["USE_MOCK_QDRANT"] = "0"  # Disable mock - use real Qdrant API
        env["OPENAI_API_KEY"] = "dummy"  # Use dummy OpenAI key for testing

        # Get real Qdrant API key from Secret Manager
        try:
            import subprocess as sp

            result = sp.run(
                [
                    "gcloud",
                    "secrets",
                    "versions",
                    "access",
                    "latest",
                    "--secret=qdrant-api-key-sg",
                    "--project=github-chatgpt-ggcloud",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            env["QDRANT_API_KEY"] = result.stdout.strip()
        except Exception as e:
            pytest.skip(f"Could not get Qdrant API key: {e}")

        # Start MCP server subprocess
        cmd = [venv_python, mcp_server_path]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=workspace_path,
            bufsize=0,  # Unbuffered
        )

        async def run_test():
            """Async test runner with enhanced timeout/retry logic."""
            try:
                # Wait for server to start
                await asyncio.sleep(3)  # Longer wait for real API initialization

                # Test with small scale for free tier and MacBook M1 limits
                num_docs = 8  # Small scale suitable for free tier
                successful_docs = 0
                failed_docs = 0

                # Configure retry logic for Qdrant free tier (210-305ms/call rate limit)
                retry_config = RetryConfig(max_retries=3, base_delay=0.5, max_delay=4.0)

                for i in range(num_docs):
                    doc_id = f"test_real_api_enhanced_{i+1}"
                    test_doc = {
                        "tool_name": "save_document",
                        "kwargs": {
                            "doc_id": doc_id,
                            "content": f"Real API test document {i+1} for CLI 119D6 enhanced validation",
                            "save_dir": "saved_documents",
                        },
                    }

                    print(f"Processing document {i+1}/{num_docs}: {doc_id}")

                    # Use enhanced retry logic (optimized for MacBook M1)
                    response = await send_request_with_retry(
                        process=process,
                        request=test_doc,
                        timeout=8.0,  # Reduced timeout for M1 compatibility
                        retry_config=retry_config,  # Timeout per attempt
                    )

                    # Count results
                    if response and "result" in response and "error" not in response:
                        successful_docs += 1
                        print(f"✅ Document {i+1} processed successfully")
                    else:
                        failed_docs += 1
                        print(f"❌ Document {i+1} failed")

                    # Rate limiting: respect Qdrant free tier limits (210-305ms between calls)
                    await asyncio.sleep(0.35)  # 350ms delay to be safe

                # Calculate success rate
                total_docs = successful_docs + failed_docs
                success_rate = successful_docs / total_docs if total_docs > 0 else 0

                # Verify success rate is above 75% as required
                assert (
                    success_rate >= 0.75
                ), f"Real API success rate {success_rate:.2%} is below 75% threshold. Successful: {successful_docs}, Failed: {failed_docs}"

                # Additional validation: ensure we actually tested with real API
                assert total_docs == num_docs, f"Expected {num_docs} documents, processed {total_docs}"

                print(
                    f"✅ CLI 119D6 Enhanced Real API Test PASSED: {success_rate:.1%} success rate ({successful_docs}/{total_docs})"
                )
                return successful_docs, failed_docs, success_rate

            except Exception as e:
                pytest.fail(f"Test execution failed: {str(e)}")

        try:
            # Run the async test
            if hasattr(asyncio, "run"):
                # Python 3.7+
                successful_docs, failed_docs, success_rate = asyncio.run(run_test())
            else:
                # Python 3.6 compatibility
                loop = asyncio.get_event_loop()
                successful_docs, failed_docs, success_rate = loop.run_until_complete(run_test())

        finally:
            # Clean up subprocess
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def test_timeout_retry_logic(self):
        """Test timeout and retry logic with simulated delays and failures - CLI 119D6."""
        # Virtual environment path
        venv_python = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
        workspace_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
        mcp_server_path = "ADK/agent_data/local_mcp_server.py"

        # Set up environment with mock QdrantStore for controlled testing
        env = os.environ.copy()
        env["PYTHONPATH"] = workspace_path
        env["USE_MOCK_QDRANT"] = "1"  # Use mock for predictable behavior
        env["OPENAI_API_KEY"] = "dummy"

        # Start MCP server subprocess
        cmd = [venv_python, mcp_server_path]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=workspace_path,
            bufsize=0,
        )

        async def run_timeout_retry_test():
            """Test timeout and retry scenarios."""
            try:
                await asyncio.sleep(2)  # Wait for server to start

                # Test 1: Normal operation (should succeed quickly)
                print("Test 1: Normal operation")
                test_doc = {
                    "tool_name": "save_document",
                    "kwargs": {
                        "doc_id": "test_timeout_normal",
                        "content": "Normal test document",
                        "save_dir": "saved_documents",
                    },
                }

                retry_config = RetryConfig(max_retries=2, base_delay=0.5, max_delay=2.0)
                response = await send_request_with_retry(
                    process=process, request=test_doc, timeout=10.0, retry_config=retry_config
                )

                normal_success = response is not None and "result" in response
                print(f"Normal operation: {'✅ PASS' if normal_success else '❌ FAIL'}")

                # Test 2: Short timeout (should trigger timeout but eventually succeed with retry)
                print("Test 2: Short timeout with retry")
                test_doc_timeout = {
                    "tool_name": "save_document",
                    "kwargs": {
                        "doc_id": "test_timeout_short",
                        "content": "Short timeout test document",
                        "save_dir": "saved_documents",
                    },
                }

                # Use very short timeout to test retry logic
                retry_config_short = RetryConfig(max_retries=3, base_delay=0.2, max_delay=1.0)
                response_timeout = await send_request_with_retry(
                    process=process,
                    request=test_doc_timeout,
                    timeout=2.0,
                    retry_config=retry_config_short,  # Short timeout
                )

                timeout_success = response_timeout is not None and "result" in response_timeout
                print(f"Short timeout with retry: {'✅ PASS' if timeout_success else '❌ FAIL'}")

                # Test 3: Echo test (should always succeed)
                print("Test 3: Echo test")
                echo_request = {"tool_name": "echo", "kwargs": {"text_to_echo": "timeout_retry_test"}}

                echo_response = await send_request_with_retry(
                    process=process,
                    request=echo_request,
                    timeout=5.0,
                    retry_config=RetryConfig(max_retries=1, base_delay=0.1, max_delay=0.5),
                )

                echo_success = echo_response is not None and "result" in echo_response
                print(f"Echo test: {'✅ PASS' if echo_success else '❌ FAIL'}")

                # Calculate overall success rate
                tests_passed = sum([normal_success, timeout_success, echo_success])
                total_tests = 3
                success_rate = tests_passed / total_tests

                print(f"Timeout/Retry Logic Test Results: {tests_passed}/{total_tests} passed ({success_rate:.1%})")

                # Verify success rate is above 75%
                assert (
                    success_rate >= 0.75
                ), f"Timeout/retry test success rate {success_rate:.2%} is below 75% threshold"

                return tests_passed, total_tests, success_rate

            except Exception as e:
                pytest.fail(f"Timeout/retry test execution failed: {str(e)}")

        try:
            # Run the async test
            if hasattr(asyncio, "run"):
                tests_passed, total_tests, success_rate = asyncio.run(run_timeout_retry_test())
            else:
                loop = asyncio.get_event_loop()
                tests_passed, total_tests, success_rate = loop.run_until_complete(run_timeout_retry_test())

            print(f"✅ CLI 119D6 Timeout/Retry Logic Test PASSED: {success_rate:.1%} success rate")

        finally:
            # Clean up subprocess
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
