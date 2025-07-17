#!/usr/bin/env python3
"""
Test script for Cloud Workflows ingestion workflow.
Tests the workflow with 8 documents to validate functionality.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from typing import Any

# Sample test documents
TEST_DOCUMENTS = [
    {
        "doc_id": f"workflow_test_doc_{i}",
        "content": f"This is test document {i} for workflow testing. It contains sample content for vectorization and tagging. Document created at {datetime.now().isoformat()}.",
        "metadata": {
            "test_batch": "cli125_workflow_test",
            "doc_index": i,
            "created_at": datetime.now().isoformat(),
            "test_type": "workflow_validation",
        },
    }
    for i in range(1, 9)
]

PROJECT_ID = "chatgpt-db-project"
LOCATION = "asia-southeast1"
WORKFLOW_NAME = "ingestion-workflow"


def execute_workflow(
    doc_id: str, content: str, metadata: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute the ingestion workflow for a single document.

    Args:
        doc_id: Document identifier
        content: Document content
        metadata: Document metadata

    Returns:
        Workflow execution result
    """
    try:
        # Prepare workflow input
        workflow_input = {"doc_id": doc_id, "content": content, "metadata": metadata}

        # Execute workflow using gcloud
        cmd = [
            "gcloud",
            "workflows",
            "run",
            WORKFLOW_NAME,
            f"--location={LOCATION}",
            f"--data={json.dumps(workflow_input)}",
        ]

        print(f"Executing workflow for {doc_id}...")
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )  # 5 minute timeout

        if result.returncode == 0:
            # Parse the workflow result
            output_lines = result.stdout.strip().split("\n")
            # Find the result line (usually the last line with JSON)
            for line in reversed(output_lines):
                if line.strip().startswith("{"):
                    try:
                        workflow_result = json.loads(line.strip())
                        return {
                            "status": "success",
                            "doc_id": doc_id,
                            "workflow_result": workflow_result,
                            "execution_time": time.time(),
                        }
                    except json.JSONDecodeError:
                        continue

            return {
                "status": "success",
                "doc_id": doc_id,
                "workflow_result": {"message": "Workflow completed successfully"},
                "raw_output": result.stdout,
                "execution_time": time.time(),
            }
        else:
            return {
                "status": "failed",
                "doc_id": doc_id,
                "error": result.stderr,
                "exit_code": result.returncode,
                "execution_time": time.time(),
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "doc_id": doc_id,
            "error": "Workflow execution timed out after 5 minutes",
            "execution_time": time.time(),
        }
    except Exception as e:
        return {
            "status": "error",
            "doc_id": doc_id,
            "error": str(e),
            "execution_time": time.time(),
        }


def test_workflow_batch(documents: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Test the workflow with a batch of documents.

    Args:
        documents: List of test documents

    Returns:
        Batch test results
    """
    start_time = time.time()
    results = []

    print(f"Starting workflow tests with {len(documents)} documents...")
    print(f"Workflow: {WORKFLOW_NAME} in {LOCATION}")
    print("-" * 60)

    for i, doc in enumerate(documents, 1):
        print(f"Testing document {i}/{len(documents)}: {doc['doc_id']}")

        result = execute_workflow(doc["doc_id"], doc["content"], doc["metadata"])

        results.append(result)

        # Print immediate result
        if result["status"] == "success":
            print(f"✅ {doc['doc_id']}: SUCCESS")
        else:
            print(
                f"❌ {doc['doc_id']}: {result['status'].upper()} - {result.get('error', 'Unknown error')}"
            )

        # Add delay between requests to avoid rate limits
        if i < len(documents):
            print("Waiting 3 seconds before next execution...")
            time.sleep(3)

    end_time = time.time()

    # Calculate statistics
    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] != "success")

    summary = {
        "test_batch": "cli125_workflow_test",
        "timestamp": datetime.now().isoformat(),
        "total_documents": len(documents),
        "successful": successful,
        "failed": failed,
        "success_rate": successful / len(documents) * 100,
        "total_time": end_time - start_time,
        "avg_time_per_doc": (end_time - start_time) / len(documents),
        "results": results,
    }

    return summary


def print_summary(summary: dict[str, Any]):
    """Print test summary results."""
    print("\n" + "=" * 60)
    print("WORKFLOW TEST SUMMARY")
    print("=" * 60)
    print(f"Test Batch: {summary['test_batch']}")
    print(f"Timestamp: {summary['timestamp']}")
    print(f"Total Documents: {summary['total_documents']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Time: {summary['total_time']:.2f} seconds")
    print(f"Avg Time per Document: {summary['avg_time_per_doc']:.2f} seconds")

    if summary["failed"] > 0:
        print("\nFAILED DOCUMENTS:")
        for result in summary["results"]:
            if result["status"] != "success":
                print(
                    f"  - {result['doc_id']}: {result['status']} - {result.get('error', 'Unknown error')}"
                )

    print("\nDETAILED RESULTS:")
    for result in summary["results"]:
        print(f"  {result['doc_id']}: {result['status']}")


def main():
    """Main test execution."""
    print("Cloud Workflows Ingestion Test - CLI 125")
    print(f"Project: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"Workflow: {WORKFLOW_NAME}")
    print(f"Documents to test: {len(TEST_DOCUMENTS)}")
    print()

    # Run the workflow tests
    summary = test_workflow_batch(TEST_DOCUMENTS)

    # Print summary
    print_summary(summary)

    # Save results to file
    results_file = f"test_outputs/workflow_test_results_{int(time.time())}.json"
    try:
        import os

        os.makedirs("test_outputs", exist_ok=True)
        with open(results_file, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved to: {results_file}")
    except Exception as e:
        print(f"\nWarning: Could not save results to file: {e}")

    # Exit with appropriate code
    if summary["success_rate"] >= 75:
        print(
            f"\n✅ Test PASSED: {summary['success_rate']:.1f}% success rate (≥75% required)"
        )
        sys.exit(0)
    else:
        print(
            f"\n❌ Test FAILED: {summary['success_rate']:.1f}% success rate (<75% required)"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
