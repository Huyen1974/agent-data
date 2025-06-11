import subprocess
import json
import time
import os
import threading
import sys

AGENT_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(AGENT_DATA_DIR, "local_mcp_server.py")
PYTHON_EXE = sys.executable  # Use the same python that runs this script


def read_output(pipe, output_lines, stop_event):
    """Reads lines from stdout or stderr in a separate thread."""
    try:
        while not stop_event.is_set():
            line = pipe.readline()
            if not line:
                break
            output_lines.append(line.strip())
        # Read any remaining lines after stop signal
        for line in pipe.readlines():
            output_lines.append(line.strip())
    except Exception as e:
        print(f"Error reading pipe: {e}")
    finally:
        pipe.close()


def run_test(test_input):
    """Runs a single test case against the MCP server."""
    print(f"--- Running Test: {test_input.get('description', 'No description')} ---")
    proc = None
    stdout_lines = []
    stderr_lines = []
    stdout_stop = threading.Event()
    stderr_stop = threading.Event()

    try:
        # Start the server process
        proc = subprocess.Popen(
            [PYTHON_EXE, SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            cwd=AGENT_DATA_DIR,
        )

        # Start reader threads
        stdout_thread = threading.Thread(target=read_output, args=(proc.stdout, stdout_lines, stdout_stop))
        stderr_thread = threading.Thread(target=read_output, args=(proc.stderr, stderr_lines, stderr_stop))
        stdout_thread.start()
        stderr_thread.start()

        # Wait a moment for the server to initialize
        time.sleep(1.5)  # Adjust if server takes longer

        # Send input JSON
        input_json = json.dumps(test_input["input"])
        print(f"Sending to stdin: {input_json}")
        proc.stdin.write(input_json + "\n")
        proc.stdin.flush()
        proc.stdin.close()  # Close stdin to signal end of input

        # Wait for the process to likely finish processing this one input
        # Wait for threads to finish reading (up to a timeout)
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        stdout_stop.set()
        stderr_stop.set()

        # Ensure threads have *really* finished even if timeout hit
        stdout_thread.join()
        stderr_thread.join()

        # Check results
        print("Stderr:")
        for line in stderr_lines:
            print(f"  {line}")
        print("Stdout:")
        result_found = False
        output_json_str = None
        for line in stdout_lines:
            print(f"  {line}")
            # Attempt to parse *every* line, looking for the first valid JSON
            if line.strip().startswith("{") and line.strip().endswith("}"):
                try:
                    output_data = json.loads(line)
                    output_json_str = line  # Store the actual JSON string found
                    # Check if this JSON contains the expected keys
                    if "result" in test_input["expected_output"] or "error" in test_input["expected_output"]:
                        break  # Found the likely result/error JSON
                except json.JSONDecodeError:
                    pass  # Ignore lines that aren't valid JSON

        if output_json_str:
            print(f"  Attempting to validate JSON: {output_json_str}")
            try:
                output_data = json.loads(output_json_str)
                if "result" in test_input["expected_output"]:
                    expected_result = test_input["expected_output"]["result"]
                    actual_result = output_data.get("result")

                    # Handle save_document timestamp by checking startswith
                    if (
                        isinstance(expected_result, str)
                        and expected_result.startswith("Document ")
                        and expected_result.endswith(" saved successfully")
                    ):
                        assert isinstance(actual_result, str) and actual_result.startswith(expected_result)
                    # Handle agent error strings returned in result field
                    elif (
                        isinstance(expected_result, str)
                        and expected_result.startswith("Error:")
                        and isinstance(actual_result, str)
                        and actual_result.startswith("Error:")
                    ):
                        assert expected_result in actual_result
                    # Default comparison for other results
                    else:
                        assert actual_result == expected_result

                    print("  ✅ Result matched expected output.")
                    result_found = True
                elif "error" in test_input["expected_output"]:
                    expected_error_substr = test_input["expected_output"]["error"]
                    actual_error = output_data.get("error", "")
                    assert expected_error_substr in actual_error
                    print("  ✅ Error matched expected output.")
                    result_found = True

            except (json.JSONDecodeError, AssertionError, TypeError) as e:
                print(f"  ❌ Validation Error: {e} for JSON: {output_json_str}")
            except Exception as e:  # Catch other potential errors during validation
                print(f"  ❌ Unexpected Validation Error: {e}")

        if not result_found:
            print("  ❌ Expected output not found or did not validate.")
            return False
        return True

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    finally:
        if proc:
            # Ensure process is terminated
            try:
                proc.terminate()  # Try graceful first
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()  # Force kill if needed
            except Exception:
                pass  # Ignore errors during cleanup
        # Ensure threads are joined even if errors occurred
        if "stdout_thread" in locals() and stdout_thread.is_alive():
            stdout_thread.join()
        if "stderr_thread" in locals() and stderr_thread.is_alive():
            stderr_thread.join()
        print("---")


# --- Test Cases ---
# Add more tests as needed
test_cases = [
    {
        "description": "Save Text - Basic",
        "input": {"tool_name": "save_text", "args": ["Hello from Test Runner!"]},
        "expected_output": {"result": "Saved text: Hello from Test Runner!"},
    },
    {
        "description": "Add Numbers - Basic",
        "input": {"tool_name": "add_numbers", "kwargs": {"number1": 10, "number2": 5.5}},
        "expected_output": {"result": 15.5},
    },
    {
        "description": "Add Numbers - Invalid Input",
        "input": {"tool_name": "add_numbers", "kwargs": {"number1": "abc", "number2": 5}},
        "expected_output": {"result": "Error: Invalid input: Both arguments must be numbers."},
    },
    {
        "description": "Multiply Numbers - Basic",
        "input": {"tool_name": "multiply_numbers", "args": [6, 7]},
        "expected_output": {"result": 42},
    },
    {
        "description": "Multiply Numbers - Invalid Input",
        "input": {"tool_name": "multiply_numbers", "args": ["a", 7]},
        "expected_output": {"result": "Error: Both arguments must be numbers (int or float)."},
    },
    {
        "description": "Save Document - Basic",
        "input": {"tool_name": "save_document", "args": ["mcp_test_doc", "Content from test runner."]},
        "expected_output": {"result": "Document 'mcp_test_doc' saved successfully"},
    },
    {
        "description": "Update Metadata - Basic",
        "input": {"tool_name": "update_metadata", "args": ["doc1", {"status": "testing"}]},
        "expected_output": {"result": {"doc_id": "doc1", "metadata_updated": {"status": "testing"}}},
    },
    {
        "description": "Query Metadata - Basic",
        "input": {"tool_name": "query_metadata", "args": ["status:testing"]},
        "expected_output": {
            "result": {"query": "status:testing", "results": ["doc001", "doc002", "doc003"]}
        },  # Mock returns fixed data
    },
    {
        "description": "Semantic Search Local - Basic",
        "input": {"tool_name": "semantic_search_local", "args": ["find test info"]},
        "expected_output": {"result": {"query": "find test info", "best_match": "doc001"}},  # Mock returns fixed data
    },
    {
        "description": "Non-existent tool",
        "input": {"tool_name": "imaginary_tool", "args": []},
        "expected_output": {"error": "Tool 'imaginary_tool' not found."},
    },
    {
        "description": "Missing tool_name",
        "input": {"args": ["some_arg"]},
        "expected_output": {"error": "Missing 'tool_name' in input JSON."},
    },
]

# --- Run Tests ---
if __name__ == "__main__":
    passed_count = 0
    failed_count = 0
    for test in test_cases:
        if run_test(test):
            passed_count += 1
        else:
            failed_count += 1

    print("\n================ Summary ================")
    print(f"Passed: {passed_count}")
    print(f"Failed: {failed_count}")
    print("=======================================")

    # Clean up the test document
    test_doc_path = os.path.join(AGENT_DATA_DIR, "saved_documents", "mcp_test_doc.txt")
    if os.path.exists(test_doc_path):
        try:
            os.remove(test_doc_path)
            print(f"Cleaned up {test_doc_path}")
        except OSError as e:
            print(f"Error cleaning up {test_doc_path}: {e}")

    sys.exit(failed_count)  # Exit with non-zero code if any tests failed
