#!/usr/bin/env python3
"""
Medium test script for MCP server with 50 documents.
Tests subprocess environment inheritance and scaled functionality.
CLI119D4 - Scale testing from 10 to 50 documents with I/O optimizations.
"""

import os
import sys
import json
import time
import subprocess
import logging
import select
from typing import List, Dict, Any

# Configure logging to ERROR level to reduce I/O
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Test configuration - optimized for MacBook M1 stability
TEST_CONFIG = {
    "num_documents": 50,  # Target 50 documents with restart mechanism
    "batch_size": 10,  # Process in batches of 10
    "concurrency": 1,  # No concurrency to avoid CPU/RAM overload
    "timeout": 60,  # Keep 60s timeout
    "success_threshold": 0.75,  # 75% success rate
    "max_retries": 3,  # Keep retry logic
    "retry_delay": 1,  # 1s delay between retries
    "doc_delay": 0.2,  # Increased delay between documents for stability
    "restart_interval": 10,  # Restart server every N documents to prevent memory issues
}

# Virtual environment path
VENV_PYTHON = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
WORKSPACE_PATH = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
MCP_SERVER_PATH = "ADK/agent_data/local_mcp_server.py"


def generate_test_documents(num_docs: int) -> List[Dict[str, Any]]:
    """Generate test documents for processing."""
    documents = []
    for i in range(num_docs):
        doc_id = f"test_doc_{i+1}"
        content = f"Test document {i+1}: This is a comprehensive test document for evaluating the MCP server's performance with medium-scale operations. The document contains meaningful content to test embedding generation and semantic search capabilities. Document ID: {i+1}, Category: Medium Scale Test"

        doc = {
            "tool_name": "save_document",
            "kwargs": {"doc_id": doc_id, "content": content, "save_dir": "saved_documents"},
        }
        documents.append(doc)
    return documents


def run_mcp_server_subprocess():
    """Start the MCP server as a subprocess with optimized buffering."""
    env = os.environ.copy()

    # Set PYTHONPATH to include the workspace directory and ensure ADK is importable
    current_pythonpath = env.get("PYTHONPATH", "")
    pythonpath_components = [WORKSPACE_PATH]
    if current_pythonpath:
        pythonpath_components.append(current_pythonpath)
    env["PYTHONPATH"] = ":".join(pythonpath_components)

    # Load environment variables from .env file
    from dotenv import load_dotenv

    load_dotenv()

    # Copy loaded env vars to subprocess environment
    for key in [
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "PUSHGATEWAY_URL",
        "SCRAPE_INTERVAL",
    ]:
        if key in os.environ:
            env[key] = os.environ[key]

    # Set mock QdrantStore and logging optimizations
    env["USE_MOCK_QDRANT"] = "1"  # Enable mock by default for testing
    env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered output

    # Ensure we're using the virtual environment Python
    cmd = [VENV_PYTHON, MCP_SERVER_PATH]

    # Only log errors to minimize I/O
    if logger.isEnabledFor(logging.ERROR):
        logger.error(f"Starting MCP server with optimized configuration")

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=WORKSPACE_PATH,
        bufsize=0,  # Unbuffered for immediate I/O
    )

    return process


def send_document_to_server(process: subprocess.Popen, document: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """Send a document to the MCP server and get response with retry logic."""
    max_retries = TEST_CONFIG["max_retries"]
    retry_delay = TEST_CONFIG["retry_delay"]

    for attempt in range(max_retries):
        try:
            # Send document as JSON
            input_json = json.dumps(document) + "\n"
            process.stdin.write(input_json)
            process.stdin.flush()

            # Read response with timeout using select
            start_time = time.time()
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    # Process has terminated
                    stderr_output = process.stderr.read()
                    raise RuntimeError(f"MCP server terminated unexpectedly: {stderr_output}")

                # Use select to check if stdout is ready for reading (Unix-like systems)
                if hasattr(select, "select"):
                    ready, _, _ = select.select([process.stdout], [], [], 0.1)
                    if ready:
                        response_line = process.stdout.readline()
                        if response_line:
                            try:
                                response = json.loads(response_line.strip())
                                return response
                            except json.JSONDecodeError as e:
                                if logger.isEnabledFor(logging.ERROR):
                                    logger.error(f"JSON parse error: {e}")
                                continue
                else:
                    # Fallback for systems without select
                    try:
                        response_line = process.stdout.readline()
                        if response_line:
                            response = json.loads(response_line.strip())
                            return response
                    except json.JSONDecodeError as e:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error(f"JSON parse error: {e}")
                        continue

                time.sleep(0.1)

            raise TimeoutError(f"No response received within {timeout} seconds")

        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return {"error": str(e)}

    return {"error": "Max retries exceeded"}


def run_test():
    """Run the medium test with 50 documents."""
    # Only essential logging
    print(f"Starting CLI119D4 medium test with {TEST_CONFIG['num_documents']} documents")

    # Generate test documents
    documents = generate_test_documents(TEST_CONFIG["num_documents"])
    print(f"Generated {len(documents)} test documents")

    # Process all documents with server restart mechanism
    all_results = []
    successful_docs = 0
    failed_docs = 0

    start_time = time.time()
    process = None

    try:
        for i, doc in enumerate(documents):
            doc_num = i + 1

            # Restart server every N documents to prevent memory issues
            if doc_num == 1 or (doc_num - 1) % TEST_CONFIG["restart_interval"] == 0:
                if process:
                    # Clean up previous server
                    try:
                        process.terminate()
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

                print(
                    f"Starting/restarting MCP server for documents {doc_num}-{min(doc_num + TEST_CONFIG['restart_interval'] - 1, TEST_CONFIG['num_documents'])}"
                )
                process = run_mcp_server_subprocess()
                time.sleep(2)  # Wait for server to start

            # Log progress every 5 documents to reduce I/O
            if doc_num % 5 == 0 or doc_num == 1:
                print(f"Processing document {doc_num}/{TEST_CONFIG['num_documents']}")

            response = send_document_to_server(process, doc, TEST_CONFIG["timeout"])
            all_results.append(response)

            # Count successes and failures
            if "error" in response:
                failed_docs += 1
            else:
                successful_docs += 1

            # Increased delay between documents for stability
            time.sleep(TEST_CONFIG["doc_delay"])

        end_time = time.time()
        total_time = end_time - start_time

        # Calculate success rate
        total_docs = successful_docs + failed_docs
        success_rate = successful_docs / total_docs if total_docs > 0 else 0

        # Summary logging (essential only)
        print(f"Test completed in {total_time:.2f} seconds")
        print(f"Documents processed: {total_docs}")
        print(f"Successful: {successful_docs}")
        print(f"Failed: {failed_docs}")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Threshold: {TEST_CONFIG['success_threshold']:.2%}")

        # Write detailed results to file
        os.makedirs(".misc", exist_ok=True)
        with open(".misc/CLI119D4_medium_test_results.txt", "w") as f:
            f.write(f"CLI119D4 Medium Test Results - 50 Documents\n")
            f.write(f"==========================================\n\n")
            f.write(f"Test Configuration:\n")
            f.write(f"- Documents: {TEST_CONFIG['num_documents']}\n")
            f.write(f"- Timeout: {TEST_CONFIG['timeout']}s\n")
            f.write(f"- Success threshold: {TEST_CONFIG['success_threshold']:.2%}\n")
            f.write(f"- Doc delay: {TEST_CONFIG['doc_delay']}s\n")
            f.write(f"- Concurrency: {TEST_CONFIG['concurrency']}\n\n")
            f.write(f"Results:\n")
            f.write(f"- Total time: {total_time:.2f} seconds\n")
            f.write(f"- Documents processed: {total_docs}\n")
            f.write(f"- Successful: {successful_docs}\n")
            f.write(f"- Failed: {failed_docs}\n")
            f.write(f"- Success rate: {success_rate:.2%}\n")
            f.write(f"- Test result: {'PASSED' if success_rate >= TEST_CONFIG['success_threshold'] else 'FAILED'}\n\n")
            f.write(f"Environment:\n")
            f.write(f"- Mock QdrantStore: Enabled\n")
            f.write(f"- Virtual environment: {VENV_PYTHON}\n")
            f.write(f"- Workspace: {WORKSPACE_PATH}\n")
            f.write(f"- Logging level: ERROR (optimized)\n\n")
            f.write(f"Performance:\n")
            f.write(f"- Average time per document: {total_time/total_docs:.2f}s\n")
            f.write(f"- Documents per minute: {total_docs/(total_time/60):.1f}\n\n")
            f.write(f"Error Summary:\n")
            error_count = {}
            for i, result in enumerate(all_results):
                if "error" in result:
                    error_type = (
                        str(result["error"])[:50] + "..." if len(str(result["error"])) > 50 else str(result["error"])
                    )
                    error_count[error_type] = error_count.get(error_type, 0) + 1
            for error, count in error_count.items():
                f.write(f"- {error}: {count} occurrences\n")

        # Determine test result
        test_passed = success_rate >= TEST_CONFIG["success_threshold"]

        if test_passed:
            print("✅ CLI119D4 MEDIUM TEST PASSED")
        else:
            print("❌ CLI119D4 MEDIUM TEST FAILED")

        return {
            "test_passed": test_passed,
            "success_rate": success_rate,
            "successful_docs": successful_docs,
            "failed_docs": failed_docs,
            "total_time": total_time,
            "total_docs": total_docs,
        }

    finally:
        # Clean up subprocess
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        result = run_test()
        sys.exit(0 if result["test_passed"] else 1)
    except Exception as e:
        print(f"Test failed with exception: {e}")
        sys.exit(1)
