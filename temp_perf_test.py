import json
import subprocess
import sys
import time

requests_list = [
    {"tool_name": "echo", "args": ["Hello"], "id": "echo-1"},
    {"tool_name": "echo", "args": [], "id": "echo-2"},
    {"tool_name": "delay", "args": [1], "id": "delay-1"},
    {"tool_name": "delay", "args": [], "id": "delay-2"},
    {"tool_name": "save_document", "args": ["doc1", "Test content"], "id": "save-1"},
    {"tool_name": "save_document", "args": [], "id": "save-2"},
    {"tool_name": "semantic_search_local", "args": ["keyword"], "id": "search-1"},
    {"tool_name": "semantic_search_local", "args": [], "id": "search-2"},
    {"tool_name": "query_metadata_faiss", "args": ["index", "key"], "id": "query-1"},
    {"tool_name": "query_metadata_faiss", "args": [], "id": "query-2"},
]
log_file_path = "/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/logs/cloud_run_performance.log"
target_url = "https://agent-data-1042559846495.asia-southeast1.run.app/execute"
latencies = []

try:
    with open(log_file_path, "a") as log_file:
        for req in requests_list:
            start = time.time()
            cmd = [
                "curl",
                "-s",
                "-X",
                "POST",
                target_url,
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps(req),
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False
            )  # Use check=False
            end = time.time()
            latency = (end - start) * 1000
            latencies.append(latency)

            status = "failed"
            response_body = result.stdout
            response_data = None
            try:
                if response_body:
                    response_data = json.loads(response_body)
                    status = response_data.get("meta", {}).get("status", "failed")
            except json.JSONDecodeError:
                status = "failed (invalid JSON)"
            except Exception:
                status = "failed (parsing error)"

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            tool_name = req["tool_name"]
            log_line = f"[{timestamp}] [{tool_name}] [{latency:.2f}ms] [{status}]\n"  # Escaped newline for log
            log_file.write(log_line)
            print(
                f"Request: {req}, Response: {response_body}"
            )  # Print raw response body

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"Average latency: {avg_latency:.2f}ms")
    else:
        print("No requests were processed.")

except Exception as e:
    print(f"An error occurred during the test script execution: {e}", file=sys.stderr)
    sys.exit(1)
