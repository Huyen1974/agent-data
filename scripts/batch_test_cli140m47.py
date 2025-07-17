#!/usr/bin/env python3
"""
CLI140m.47 Enhanced Batch Test Script
Modified to log detailed test failures (F), slow tests (S), and skipped tests
Preparing for Vòng 1 Batch test with ≤3 tests/batch, runtime <10s
"""

import csv
import os
import subprocess
import time
from datetime import datetime


def log_with_timestamp(message, log_file="logs/test_fixes.log"):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    log_entry = f"{timestamp} - {message}\n"
    print(log_entry.strip())
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry)


def extract_test_names():
    """Extract test names using pytest --collect-only"""
    log_with_timestamp("Collecting test names using pytest --collect-only")

    try:
        result = subprocess.run(
            ["pytest", "--collect-only", "-q", "--qdrant-mock"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        test_names = []
        lines = result.stdout.split("\n")

        for line in lines:
            line = line.strip()
            if "::" in line and (line.startswith("tests/") or line.startswith("ADK/")):
                test_names.append(line)

        log_with_timestamp(f"Collected {len(test_names)} tests")
        return test_names

    except Exception as e:
        log_with_timestamp(f"Error collecting tests: {e}")
        return []


def create_batches(test_names, batch_size=3):
    """Create batches of tests with specified size (≤3)"""
    batches = []
    for i in range(0, len(test_names), batch_size):
        batch = test_names[i : i + batch_size]
        batches.append(batch)

    log_with_timestamp(f"Created {len(batches)} batches with batch size ≤{batch_size}")
    return batches


def run_test_batch(batch, batch_num, total_batches, csv_writer):
    """Run a single batch of tests with enhanced logging for F, S, skipped tests"""

    # Reset testmondata for each batch
    subprocess.run(["rm", "-f", ".testmondata"], capture_output=True)

    # Create -k parameter for batch tests using just test names
    if len(batch) == 1:
        # Extract just the test method name for -k parameter
        k_param = batch[0].split("::")[-1]
    else:
        # Use OR logic for multiple test names
        test_names = [test.split("::")[-1] for test in batch]
        k_param = " or ".join(test_names)

    log_with_timestamp(f"Batch {batch_num}/{total_batches}: Running {len(batch)} tests")
    log_with_timestamp(f"Batch {batch_num} tests: {batch}")

    # Construct pytest command with enhanced options and MacBook M1 safety
    cmd = [
        "pytest",
        "-k",
        k_param,
        "--qdrant-mock",
        "--timeout=8",
        "--tb=short",
        "--durations=10",
        "-v",
        "-rs",
        f"--junit-xml=test_results_batch_{batch_num}.xml",
    ]

    log_with_timestamp(f"Batch {batch_num} command: {' '.join(cmd)}")

    # Run the command and capture output
    start_time = time.time()
    try:
        # Use 24s timeout (3×8s per test), with special case for timeout_fake tests
        test_timeout = 10 if any("timeout_fake" in test for test in batch) else 24
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=test_timeout
        )
        end_time = time.time()
        runtime = end_time - start_time

        log_with_timestamp(f"Batch {batch_num} completed in {runtime:.2f}s")
        log_with_timestamp(f"Batch {batch_num} exit code: {result.returncode}")

        # Parse and log individual test results
        parse_enhanced_test_results(
            result.stdout, result.stderr, batch_num, csv_writer, runtime
        )

        # Check runtime compliance (must be <10s)
        if runtime > 10.0:
            log_with_timestamp(
                f"ERROR: Batch {batch_num} exceeded 10s runtime limit ({runtime:.2f}s) - UNACCEPTABLE"
            )
            return False, runtime
        elif runtime > 8.0:
            log_with_timestamp(
                f"WARNING: Batch {batch_num} slow runtime ({runtime:.2f}s) approaching limit"
            )

        return result.returncode == 0, runtime

    except subprocess.TimeoutExpired:
        end_time = time.time()
        runtime = end_time - start_time
        log_with_timestamp(f"ERROR: Batch {batch_num} timed out after {runtime:.2f}s")

        # Log timeout tests separately with detailed information
        for i, test in enumerate(batch):
            test_name = test.split("::")[-1] if "::" in test else test
            test_file = test.split("::")[0] if "::" in test else f"tests/{test}.py"
            log_with_timestamp(
                f"Test TIMEOUT: {test_name}, File: {test_file}, Runtime: {runtime:.2f}s, Log: Line timeout-{i+1}"
            )

            csv_writer.writerow(
                [
                    test_name,
                    test_file,
                    "TIMEOUT",
                    f"Timeout after {runtime:.2f}s",
                    f"Line timeout-{i+1}",
                ]
            )

        return False, runtime

    except Exception as e:
        end_time = time.time()
        runtime = end_time - start_time
        log_with_timestamp(f"ERROR: Batch {batch_num} failed with exception: {e}")
        return False, runtime


def parse_enhanced_test_results(stdout, stderr, batch_num, csv_writer, batch_runtime):
    """Enhanced parsing to log test F (failures), S (slow), and skipped tests"""

    lines = stdout.split("\n") if stdout else []

    for i, line in enumerate(lines):
        line_stripped = line.strip()

        # Look for test results with different patterns
        if "::" in line_stripped:
            # Handle timeout/failed tests
            if "FAILED" in line_stripped and "[" in line_stripped:
                # Extract test info from patterns like: tests/test_timeout_fake.py::TestTimeoutFake::test_timeout_fake FAILED [ 50%]
                test_full_name = line_stripped.split(" FAILED")[0].strip()
                test_name = test_full_name.split("::")[-1]
                test_file = test_full_name.split("::")[0]

                # Check if it's a timeout failure
                if "Timeout" in stdout or "timeout" in stdout.lower():
                    log_with_timestamp(
                        f"Test TIMEOUT: {test_name}, File: {test_file}, Runtime: 8.0s+, Log: Line {i+1}"
                    )
                    csv_writer.writerow(
                        [
                            test_name,
                            test_file,
                            "TIMEOUT",
                            "Timeout >8s from pytest-timeout",
                            f"Line {i+1}",
                        ]
                    )
                else:
                    error_info = extract_error_details(lines, i)
                    log_with_timestamp(
                        f"Test F: {test_name}, File: {test_file}, Error: {error_info}, Log: Line {i+1}"
                    )
                    csv_writer.writerow(
                        [test_name, test_file, "FAILED", error_info, f"Line {i+1}"]
                    )

            elif "PASSED" in line_stripped and "[" in line_stripped:
                # Extract test info from patterns like: tests/test_timeout_fake.py::TestTimeoutFake::test_timeout_fake_short PASSED [100%]
                test_full_name = line_stripped.split(" PASSED")[0].strip()
                test_name = test_full_name.split("::")[-1]
                test_file = test_full_name.split("::")[0]

                # Check if it's a slow test (>8s runtime)
                if batch_runtime > 8.0:
                    log_with_timestamp(
                        f"Test S: {test_name}, File: {test_file}, Runtime: {batch_runtime:.2f}s, Marker: @pytest.mark.slow"
                    )
                    csv_writer.writerow(
                        [
                            test_name,
                            test_file,
                            "SLOW",
                            f"{batch_runtime:.2f}s runtime",
                            f"Line {i+1}",
                        ]
                    )
                else:
                    log_with_timestamp(
                        f"Test: {test_name}, Status: PASSED, Runtime: {batch_runtime:.2f}s, Log: Line {i+1}"
                    )
                    csv_writer.writerow(
                        [
                            test_name,
                            test_file,
                            "PASSED",
                            f"{batch_runtime:.2f}s runtime",
                            f"Line {i+1}",
                        ]
                    )

            elif "SKIPPED" in line_stripped and "[" in line_stripped:
                # Extract test info from patterns like: tests/test_name.py::TestClass::test_method SKIPPED [reason]
                test_full_name = line_stripped.split(" SKIPPED")[0].strip()
                test_name = test_full_name.split("::")[-1]
                test_file = test_full_name.split("::")[0]

                skip_reason = extract_skip_reason(lines, i)
                log_with_timestamp(
                    f"Test SKIPPED: {test_name}, File: {test_file}, Reason: {skip_reason}, Log: Line {i+1}"
                )
                csv_writer.writerow(
                    [test_name, test_file, "SKIPPED", skip_reason, f"Line {i+1}"]
                )


def extract_error_details(lines, start_index):
    """Extract error details from test failure output"""
    error_details = []

    # Look ahead for error information
    for i in range(start_index + 1, min(start_index + 10, len(lines))):
        line = lines[i].strip()
        if "AssertionError" in line or "Error:" in line or "assert" in line:
            error_details.append(line)
            break
        elif line.startswith("E ") and len(line) > 2:
            error_details.append(line[2:])  # Remove "E " prefix
            break

    return "; ".join(error_details) if error_details else "Unknown error"


def extract_skip_reason(lines, start_index):
    """Extract skip reason from test output"""
    # Look for skip reason in the same line or following lines
    for i in range(start_index, min(start_index + 5, len(lines))):
        line = lines[i].strip()
        if "SKIPPED" in line and "reason:" in line.lower():
            parts = line.split("reason:", 1)
            if len(parts) > 1:
                return parts[1].strip()
        elif "@pytest.mark.deferred" in line:
            return "@pytest.mark.deferred"
        elif "skip" in line.lower() and "condition" in line.lower():
            return "Skip condition met"

    return "Skipped - reason unknown"


def main():
    """Main execution function for CLI140m.47"""

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Log script start
    log_with_timestamp("=" * 80)
    log_with_timestamp("CLI140m.47 Enhanced Batch Test Script Started")
    log_with_timestamp("Date: June 18, 2025, 13:47 +07")
    log_with_timestamp("Objective: Log detailed test F, S, Skipped, Timeout for Vòng 1")
    log_with_timestamp("Reusing CLI140m.39 batch approach with enhanced logging")
    log_with_timestamp("=" * 80)

    # Extract test names
    test_names = extract_test_names()

    if not test_names:
        log_with_timestamp("ERROR: No test names collected")
        return

    # Create batches (≤3 tests per batch)
    batches = create_batches(test_names, batch_size=3)

    # Prepare CSV output file
    csv_filename = "test_summary_cli140m47.txt"

    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        # CSV Header
        csv_writer.writerow(
            ["name", "file", "status", "error/runtime/reason", "log_line"]
        )

        # Run first ~10 tests to verify log format (production mode for Vòng 1)
        test_batches = batches[:4]  # First 4 batches (~12 tests)

        successful_batches = 0
        failed_batches = 0
        total_runtime = 0

        log_with_timestamp(
            f"Running first {len(test_batches)} batches (~{len(test_batches)*3} tests) to verify log format"
        )

        for batch_num, batch in enumerate(test_batches, 1):
            log_with_timestamp("\n" + "=" * 60)
            log_with_timestamp(f"STARTING BATCH {batch_num}/{len(test_batches)}")

            success, runtime = run_test_batch(
                batch, batch_num, len(test_batches), csv_writer
            )
            total_runtime += runtime

            if success:
                successful_batches += 1
            else:
                failed_batches += 1

            log_with_timestamp(
                f"BATCH {batch_num} COMPLETED - Success: {success}, Runtime: {runtime:.2f}s"
            )

            # Stop if runtime exceeds 10s (UNACCEPTABLE FAILURE)
            if runtime > 10.0:
                log_with_timestamp(
                    "STOPPING: Runtime >10s detected - MacBook M1 hang prevention"
                )
                break

            # Brief pause to prevent MacBook M1 overload
            time.sleep(0.5)

    # Log summary
    log_with_timestamp("\n" + "=" * 80)
    log_with_timestamp("CLI140m.47 BATCH TEST VERIFICATION COMPLETED")
    log_with_timestamp(f"Verification batches run: {len(test_batches)}")
    log_with_timestamp(f"Successful batches: {successful_batches}")
    log_with_timestamp(f"Failed batches: {failed_batches}")
    log_with_timestamp(f"Total runtime: {total_runtime:.2f}s")
    log_with_timestamp(f"Average batch runtime: {total_runtime/len(test_batches):.2f}s")
    log_with_timestamp(f"CSV output saved to: {csv_filename}")
    log_with_timestamp("=" * 80)

    # Display CSV content sample
    log_with_timestamp("CSV Output Sample:")
    try:
        with open(csv_filename, encoding="utf-8") as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:10]):  # First 10 lines
                log_with_timestamp(f"CSV Line {i+1}: {line.strip()}")
    except Exception as e:
        log_with_timestamp(f"Error reading CSV file: {e}")


if __name__ == "__main__":
    main()
