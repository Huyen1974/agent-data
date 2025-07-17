#!/usr/bin/env python3
"""
Simple test script to verify MCP server communication.
CLI119D4 - Debug subprocess communication.
"""

import json
import os
import subprocess
import sys
import time

# Virtual environment path
VENV_PYTHON = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/setup/venv/bin/python"
WORKSPACE_PATH = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
MCP_SERVER_PATH = "ADK/agent_data/local_mcp_server.py"


def test_simple_communication():
    """Test simple communication with MCP server."""
    print("Testing simple MCP server communication...")

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = WORKSPACE_PATH
    env["USE_MOCK_QDRANT"] = "1"
    env["OPENAI_API_KEY"] = "dummy"
    env["PYTHONUNBUFFERED"] = "1"

    # Start server
    cmd = [VENV_PYTHON, MCP_SERVER_PATH]
    print(f"Starting server: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=WORKSPACE_PATH,
        bufsize=0,  # Unbuffered
    )

    try:
        # Wait for server to start
        time.sleep(2)

        # Send a simple test document
        test_doc = {
            "tool_name": "save_document",
            "kwargs": {
                "doc_id": "simple_test",
                "content": "Simple test content",
                "save_dir": "saved_documents",
            },
        }

        print(f"Sending test document: {test_doc}")
        input_json = json.dumps(test_doc) + "\n"
        process.stdin.write(input_json)
        process.stdin.flush()

        # Try to read response with timeout
        print("Waiting for response...")
        start_time = time.time()
        timeout = 10  # Short timeout for simple test

        while time.time() - start_time < timeout:
            if process.poll() is not None:
                print("Process terminated unexpectedly")
                stderr_output = process.stderr.read()
                print(f"Stderr: {stderr_output}")
                return False

            # Check if there's output available
            try:
                # Use a very short timeout for readline
                import select

                if hasattr(select, "select"):
                    ready, _, _ = select.select([process.stdout], [], [], 0.1)
                    if ready:
                        response_line = process.stdout.readline()
                        if response_line:
                            print(f"Received response: {response_line.strip()}")
                            try:
                                response = json.loads(response_line.strip())
                                print(f"Parsed response: {response}")
                                return True
                            except json.JSONDecodeError as e:
                                print(f"JSON parse error: {e}")
                                continue
            except Exception as e:
                print(f"Error reading response: {e}")

            time.sleep(0.1)

        print("Timeout waiting for response")
        return False

    finally:
        # Clean up
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    success = test_simple_communication()
    print(f"Simple test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
