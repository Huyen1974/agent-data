import json
import os
import subprocess
import sys
import time

requests = [
    {"tool_name": "echo", "args": ["Hello"], "id": "echo-1"},
    {"tool_name": "echo", "args": [], "id": "echo-2"},  # Invalid echo
    {"tool_name": "delay", "args": [1], "id": "delay-1"},
    {
        "tool_name": "delay",
        "args": [],
        "id": "delay-2",
    },  # Invalid delay (might still work depending on tool handling)
    {
        "tool_name": "save_document",
        "args": ["doc_perf_test", "Test content"],
        "id": "save-1",
    },
    {"tool_name": "save_document", "args": [], "id": "save-2"},  # Invalid save
    {"tool_name": "semantic_search_local", "args": ["keyword"], "id": "search-1"},
    {
        "tool_name": "semantic_search_local",
        "args": [],
        "id": "search-2",
    },  # Invalid search
    {
        "tool_name": "query_metadata",
        "args": ["doc_perf_test", "key"],
        "id": "query-1",
    },  # Changed key for potential validity
    {"tool_name": "query_metadata", "args": [], "id": "query-2"},  # Invalid query
]

log_dir = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/logs"
log_file_path = os.path.join(log_dir, "performance_test.log")
agent_module = "agent_data_manager.mcp.mcp_agent"
latencies = []

os.makedirs(log_dir, exist_ok=True)

print(f"Starting performance test. Logging to: {log_file_path}")
sys.stdout.flush()

with open(log_file_path, "a") as log_file:
    for i, req in enumerate(requests):
        req_start = time.time()

        # Prepare command without complex shell piping inside python string
        json_input = json.dumps(req)
        proc = subprocess.run(
            [sys.executable, "-m", agent_module],  # Use sys.executable for portability
            input=json_input,
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit
        )

        req_end = time.time()
        latency = (req_end - req_start) * 1000
        latencies.append(latency)

        stdout_content = proc.stdout.strip()
        stderr_content = proc.stderr.strip()

        # Determine status based on return code and presence of "error" in stdout JSON
        status = "failed"
        # Find the last line that looks like JSON
        last_json_line = None
        for line in reversed(stdout_content.splitlines()):
            if line.strip().startswith("{") and line.strip().endswith("}"):
                last_json_line = line.strip()
                break

        if proc.returncode == 0 and last_json_line:
            try:
                response_json = json.loads(last_json_line)
                # Check for explicit error field or error status in meta
                if (
                    response_json.get("error") is None
                    and response_json.get("meta", {}).get("status") != "error"
                ):
                    status = "success"
                else:
                    status = (
                        "failed (error in JSON)"  # Tool executed but returned an error
                    )
            except json.JSONDecodeError:
                status = "failed (bad json output)"  # Output wasn't valid JSON
        elif proc.returncode != 0:
            status = f"failed (exit code {proc.returncode})"
        else:
            status = "failed (no json output)"

        # # Special case: if the tool itself is invalid (e.g., missing args), stdout might contain error JSON
        # Commenting this out as it causes false negatives
        # if status == 'success' and 'error' in stdout_content.lower():
        #      status = 'failed (error in output)'

        log_line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] [{req.get("tool_name", "N/A")}] [{latency:.2f}ms] [{status}]\n'
        log_file.write(log_line)

        print(
            f'Request {i+1}/{len(requests)}: Tool={req.get("tool_name", "N/A")}, Status={status}, Latency={latency:.2f}ms'
        )
        sys.stdout.flush()

        if status != "success":
            print(f"  Stdout: {stdout_content}")
            print(f"  Stderr: {stderr_content}")

    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    print(
        f"Performance test complete. Average latency (incl. startup): {avg_latency:.2f}ms"
    )
    log_file.write(
        f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] [Summary] Average Latency (incl. startup): {avg_latency:.2f}ms\n'
    )

print(f"Performance log saved to {log_file_path}")
