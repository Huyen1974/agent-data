import json
import time
import os
import subprocess
import sys
import select
import threading

log_file_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/logs/performance_test.log"
agent_script_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/ADK/agent_data/mcp/mcp_agent.py"
agent_module = "agent_data_manager.mcp.mcp_agent"
workspace_dir = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents"
# requests_list = [ ... ] # Original list commented out
requests_list = [
    {"tool_name": "echo", "args": ["Hello from Cursor"], "id": "cursor-echo-1"},
    {"tool_name": "save_document", "args": ["cursor_doc", "Content from Cursor"], "id": "cursor-save-1"},
]
latencies = []
timeout_seconds = 15  # Slightly longer timeout

# Function to continuously read stderr
stderr_lines = []
stderr_lock = threading.Lock()


def read_stderr(pipe):
    try:
        for line in iter(pipe.readline, ""):
            with stderr_lock:
                stderr_lines.append(line.strip())
            print(f"[AGENT_STDERR] {line.strip()}", file=sys.stderr)
    except Exception as e:
        print(f"[STDERR_THREAD_ERROR] {e}", file=sys.stderr)
    finally:
        pipe.close()


print(f"Starting agent module: {agent_module} from {workspace_dir}")
agent_process = None
stderr_thread = None

try:
    agent_process = subprocess.Popen(
        ["python3", "-m", agent_module],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True,
        cwd=workspace_dir,
    )

    # Start stderr reader thread
    stderr_thread = threading.Thread(target=read_stderr, args=(agent_process.stderr,), daemon=True)
    stderr_thread.start()

    print("Waiting for agent to initialize...")
    time.sleep(3)  # Allow more time for init + potential logs

    if agent_process.poll() is not None:
        print(f"Agent failed to start. Exit code: {agent_process.returncode}", file=sys.stderr)
        # Stderr already being captured by thread
        sys.exit(1)
    print("Agent started successfully.")

    with open(log_file_path, "a") as log_file:
        for req in requests_list:
            print(f"\nSending request: {json.dumps(req)}")
            start_time = time.time()
            response_received = False

            try:
                if agent_process.stdin.closed:
                    print("Agent stdin pipe is closed.", file=sys.stderr)
                    break

                agent_process.stdin.write(json.dumps(req) + "\n")
                agent_process.stdin.flush()
                print("Request sent, waiting for response...")

                # Read stdout line by line with timeout
                response_line = None
                read_timeout = time.time() + timeout_seconds
                while time.time() < read_timeout:
                    ready_to_read, _, _ = select.select([agent_process.stdout], [], [], 0.1)  # Short poll
                    if ready_to_read:
                        line = agent_process.stdout.readline()
                        if not line:  # EOF
                            print("Agent exited unexpectedly (EOF on stdout read).", file=sys.stderr)
                            agent_process.poll()  # Update return code
                            break
                        line = line.strip()
                        if not line:  # Skip empty lines
                            continue

                        # Attempt to parse as JSON
                        try:
                            response_json = json.loads(line)
                            # Basic check if it looks like a response (has 'id' or 'meta')
                            if isinstance(response_json, dict) and (
                                response_json.get("id") == req.get("id") or "meta" in response_json
                            ):
                                response_line = line
                                response_received = True
                                break  # Found JSON response for this request ID or with meta
                            else:
                                print(f"[AGENT_STDOUT_NON_RESP_JSON] {line}")  # Log unexpected JSON
                        except json.JSONDecodeError:
                            print(f"[AGENT_STDOUT_LOG] {line}")  # Log non-JSON lines (likely logs)
                    # Check if agent process exited while waiting
                    if agent_process.poll() is not None:
                        print(f"Agent exited while waiting for response for request {req.get('id')}.", file=sys.stderr)
                        break  # Exit inner loop
                # End of read loop
                if agent_process.poll() is not None and not response_received:
                    # Agent exited before response or timeout
                    break  # Exit outer loop

                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                status = "unknown"

                if response_received and response_line:
                    latencies.append(latency_ms)
                    try:
                        response_data = json.loads(response_line)
                        status = response_data.get("meta", {}).get(
                            "status", "success" if "result" in response_data else "error"
                        )
                        print(f"Received response ({latency_ms:.2f}ms): {response_line}")
                    except json.JSONDecodeError:  # Should not happen if response_line was parsed before
                        status = "failed (internal parse error)"
                        print(f"Internal Error: Failed to re-parse valid JSON line: {response_line}")
                elif agent_process.poll() is not None:
                    status = "failed (agent exited)"
                    print(f'Agent exited before sending response for {req.get("id")}. Latency: {latency_ms:.2f}ms')
                else:  # Timeout
                    status = "failed (timeout)"
                    print(
                        f"Timeout ({latency_ms:.2f}ms) waiting for JSON response from agent for request: {json.dumps(req)}"
                    )

                log_line = (
                    f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] [{req["tool_name"]}] [{latency_ms:.2f}ms] [{status}]\n'
                )
                log_file.write(log_line)
                log_file.flush()

            except (BrokenPipeError, OSError) as e:
                print(f"Error communicating with agent: {e}. Agent might have terminated.", file=sys.stderr)
                break  # Exit loop
            except Exception as e:
                print(f"Unexpected error in request loop: {e}", file=sys.stderr)
                # Optionally break here depending on error severity

    # After loop completes or breaks
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"\nAverage latency for received responses: {avg_latency:.2f}ms")
        if avg_latency <= 20000:
            print("Average latency is within the 20-second limit.")
        else:
            print("Warning: Average latency exceeds the 20-second limit.")
    else:
        print("\nNo valid JSON responses received successfully.")

except Exception as e:
    print(f"An error occurred during the test setup or execution: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc()

finally:
    if agent_process:
        print("\nTerminating agent process...")
        # Close stdin first to signal agent
        if not agent_process.stdin.closed:
            try:
                agent_process.stdin.close()
            except Exception as e:
                print(f"Error closing agent stdin: {e}", file=sys.stderr)

        if agent_process.poll() is None:
            try:
                agent_process.terminate()
                agent_process.wait(timeout=5)
                print("Agent terminated gracefully.")
            except subprocess.TimeoutExpired:
                print("Agent did not terminate gracefully, killing...")
                agent_process.kill()
                agent_process.wait()
                print("Agent killed.")
            except Exception as e:
                print(f"Error during agent termination: {e}", file=sys.stderr)
                if agent_process.poll() is None:
                    agent_process.kill()
                    agent_process.wait()
        else:
            print(f"Agent process already terminated with code: {agent_process.returncode}")

        # Wait for stderr thread to finish
        if stderr_thread and stderr_thread.is_alive():
            print("Waiting for stderr thread to finish...")
            stderr_thread.join(timeout=2)
            if stderr_thread.is_alive():
                print("Stderr thread did not finish.", file=sys.stderr)

        # Read any remaining output/errors (should be handled by thread, but check)
        try:
            stdout, _ = agent_process.communicate(timeout=1)
            if stdout:
                print(f"Agent final stdout:\n{stdout.strip()}")
        except Exception:
            pass  # Ignore errors here, likely already closed

    print("MCP test script finished.")
    print("Final captured stderr lines:")
    with stderr_lock:
        for line in stderr_lines:
            print(f"[FINAL_STDERR] {line}")
