#!/usr/bin/env python3
"""
Test real FastAPI /cskh_query endpoint latency - CLI140e.3.5
Validates that the deployed FastAPI achieves real-workload latency targets
"""

import json
import logging
import time
from typing import Any

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI endpoint
FASTAPI_URL = (
    "https://asia-southeast1-chatgpt-db-project.cloudfunctions.net/api-mcp-gateway-v2"
)


def test_fastapi_health():
    """Test FastAPI health endpoint"""
    try:
        start_time = time.time()
        response = requests.get(f"{FASTAPI_URL}/health", timeout=10)
        latency = time.time() - start_time

        logger.info(f"Health check: {response.status_code} - {latency:.3f}s")

        if response.status_code == 200:
            health_data = response.json()
            logger.info(f"Status: {health_data.get('status')}")
            logger.info(f"Services: {health_data.get('services')}")
            return True, latency, health_data
        else:
            return False, latency, {"error": f"HTTP {response.status_code}"}

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False, 0, {"error": str(e)}


def test_fastapi_cskh_query_latency(
    queries: list[str], target_latency: float = 0.5
) -> dict[str, Any]:
    """Test CSKH query latency using real FastAPI endpoint"""
    results = {
        "queries_tested": len(queries),
        "target_latency_seconds": target_latency,
        "results": [],
        "average_latency": 0.0,
        "max_latency": 0.0,
        "min_latency": float("inf"),
        "queries_under_target": 0,
        "queries_over_target": 0,
        "authentication_required": False,
    }

    logger.info(f"Testing CSKH query latency for {len(queries)} queries...")

    total_time = 0.0

    for i, query in enumerate(queries):
        start_time = time.time()

        try:
            # Make request to FastAPI endpoint
            payload = {"query_text": query, "limit": 3, "score_threshold": 0.6}

            response = requests.post(
                f"{FASTAPI_URL}/cskh_query",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15,
            )

            end_time = time.time()
            latency = end_time - start_time
            total_time += latency

            # Handle authentication requirement
            if response.status_code == 401:
                results["authentication_required"] = True
                logger.warning(f"Query {i+1}: Authentication required - {latency:.3f}s")

                query_result = {
                    "query_index": i,
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "latency_seconds": round(latency, 3),
                    "status": "auth_required",
                    "results_found": 0,
                    "under_target": latency < target_latency,
                    "response_code": response.status_code,
                }
            else:
                # Parse response
                try:
                    response_data = response.json()
                    status = response_data.get("status", "unknown")
                    results_found = len(response_data.get("results", []))
                except:
                    status = f"http_{response.status_code}"
                    results_found = 0

                query_result = {
                    "query_index": i,
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "latency_seconds": round(latency, 3),
                    "status": status,
                    "results_found": results_found,
                    "under_target": latency < target_latency,
                    "response_code": response.status_code,
                }

                logger.info(
                    f"Query {i+1}: {latency:.3f}s ({response.status_code}) - {'✓' if latency < target_latency else '✗'}"
                )

            results["results"].append(query_result)

            # Update statistics
            results["max_latency"] = max(results["max_latency"], latency)
            results["min_latency"] = min(results["min_latency"], latency)

            if latency < target_latency:
                results["queries_under_target"] += 1
            else:
                results["queries_over_target"] += 1

        except Exception as e:
            logger.error(f"Query {i+1} failed: {e}")
            results["results"].append(
                {
                    "query_index": i,
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "latency_seconds": 0,
                    "status": "error",
                    "results_found": 0,
                    "under_target": False,
                    "error": str(e),
                }
            )

    # Calculate average
    if results["queries_tested"] > 0:
        results["average_latency"] = round(total_time / results["queries_tested"], 3)

    return results


def main():
    """Main test function"""
    print("🚀 Starting FastAPI CSKH Query Latency Test - CLI140e.3.5")
    print("=" * 60)

    # Test health first
    print("\n📋 Testing FastAPI Health...")
    health_ok, health_latency, health_data = test_fastapi_health()

    if not health_ok:
        print(f"❌ Health check failed: {health_data}")
        return

    print(f"✅ Health check passed: {health_latency:.3f}s")
    print(f"   Status: {health_data.get('status')}")
    print(f"   Services: {health_data.get('services')}")

    # Test CSKH queries
    print("\n⚡ Testing CSKH Query Latency...")

    test_queries = [
        "How do I reset my password?",
        "Billing inquiry about monthly charges",
        "Technical support for connection issues",
        "Account management and profile updates",
        "Product information and features",
    ]

    results = test_fastapi_cskh_query_latency(test_queries, target_latency=0.5)

    # Print results
    print("\n📊 FASTAPI CSKH LATENCY TEST RESULTS")
    print("=" * 50)
    print(f"Queries tested: {results['queries_tested']}")
    print(f"Average latency: {results['average_latency']}s")
    print(f"Min latency: {results['min_latency']:.3f}s")
    print(f"Max latency: {results['max_latency']:.3f}s")
    print(f"Target: <{results['target_latency_seconds']}s")
    print(
        f"Success rate: {(results['queries_under_target']/results['queries_tested']*100):.1f}%"
    )

    if results["authentication_required"]:
        print("⚠️  Authentication required - testing endpoint connectivity only")

    print("\n📝 Individual Query Results:")
    for result in results["results"]:
        status_icon = "✅" if result["under_target"] else "❌"
        print(
            f"  {status_icon} Query {result['query_index']+1}: {result['latency_seconds']}s - {result['query']}"
        )
        print(
            f"     Status: {result['status']} (HTTP {result.get('response_code', 'N/A')})"
        )

    # Save results
    with open("logs/fastapi_cskh_latency.log", "w") as f:
        json.dump(results, f, indent=2)

    print("\n💾 Results saved to logs/fastapi_cskh_latency.log")

    # Determine success
    target_met = results["average_latency"] < results["target_latency_seconds"]
    if target_met:
        print(
            f"\n🎉 SUCCESS: Average latency ({results['average_latency']}s) meets target (<{results['target_latency_seconds']}s)"
        )
    else:
        print(
            f"\n⚠️  WARNING: Average latency ({results['average_latency']}s) exceeds target (<{results['target_latency_seconds']}s)"
        )

    return results


if __name__ == "__main__":
    main()
