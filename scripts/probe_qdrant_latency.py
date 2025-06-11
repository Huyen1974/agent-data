#!/usr/bin/env python3
"""
CLI112C: Qdrant Cloud Latency Measurement Script

This script measures baseline latency from development location (Vietnam) to Qdrant Cloud (us-east4-0):
1. Ping latency to the endpoint
2. Simple search operation latency
"""

import subprocess
import time
import datetime
from typing import Optional
from qdrant_client import QdrantClient
import ping3


def log_result(action: str, latency_ms: float, status: str, log_file: str = "logs/latency_probe.log"):
    """Log latency measurement result with timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{action}] [{latency_ms:.2f}ms] [{status}]\n"

    try:
        with open(log_file, "a") as f:
            f.write(log_entry)
        print(f"📝 Logged: {log_entry.strip()}")
    except Exception as e:
        print(f"❌ Failed to write to log: {e}")


def get_api_key_from_secret_manager() -> Optional[str]:
    """Retrieve Qdrant API key from Google Cloud Secret Manager."""
    try:
        result = subprocess.run(
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

        api_key = result.stdout.strip()
        print("✅ Successfully retrieved API key from Secret Manager")
        return api_key
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to retrieve API key from Secret Manager: {e}")
        print(f"stderr: {e.stderr}")
        return None


def measure_ping_latency(hostname: str) -> Optional[float]:
    """Measure ping latency to hostname."""
    print(f"🏓 Measuring ping latency to {hostname}...")

    try:
        # Use ping3 for Python-based ping
        response_time = ping3.ping(hostname, timeout=10)

        if response_time is not None:
            latency_ms = response_time * 1000  # Convert to milliseconds
            print(f"✅ Ping successful: {latency_ms:.2f}ms")
            return latency_ms
        else:
            print("❌ Ping failed: No response")
            return None

    except Exception as e:
        print(f"❌ Ping error: {e}")
        # Fallback to system ping if ping3 fails
        try:
            print("🔄 Trying system ping as fallback...")
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "10000", hostname], capture_output=True, text=True, check=True
            )

            # Parse ping output for latency
            output_lines = result.stdout.split("\n")
            for line in output_lines:
                if "time=" in line:
                    time_part = line.split("time=")[1].split("ms")[0].strip()
                    latency_ms = float(time_part)
                    print(f"✅ System ping successful: {latency_ms:.2f}ms")
                    return latency_ms

            print("❌ Could not parse ping output")
            return None

        except Exception as fallback_e:
            print(f"❌ System ping also failed: {fallback_e}")
            return None


def measure_search_latency(client: QdrantClient) -> Optional[float]:
    """Measure simple search operation latency."""
    print("🔍 Measuring simple search latency...")

    try:
        # Create a dummy vector for search (dimension 5 as suggested)
        dummy_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Get available collections first
        collections = client.get_collections()
        if not collections.collections:
            print("⚠️  No collections available for search test")
            return None

        # Use the first available collection
        collection_name = collections.collections[0].name
        print(f"📦 Using collection: {collection_name}")

        # Measure search operation
        start_time = time.time()

        try:
            search_result = client.search(
                collection_name=collection_name,
                query_vector=dummy_vector,
                limit=1,
                with_payload=False,
                with_vectors=False,
            )

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            print(f"✅ Search successful: {latency_ms:.2f}ms")
            print(f"📊 Results returned: {len(search_result)}")
            return latency_ms

        except Exception as search_e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Even if search fails, we got a response, so we can measure latency
            if "vector dimension" in str(search_e).lower() or "collection" in str(search_e).lower():
                print(f"⚠️  Search failed (expected - dimension/collection mismatch): {latency_ms:.2f}ms")
                print(f"   Error: {search_e}")
                return latency_ms
            else:
                print(f"❌ Search failed with unexpected error: {search_e}")
                return None

    except Exception as e:
        print(f"❌ Search operation error: {e}")
        return None


def create_qdrant_client(api_key: str) -> Optional[QdrantClient]:
    """Create and test Qdrant client connection."""
    cluster_endpoint = "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io"

    try:
        print("🔗 Creating Qdrant client...")
        client = QdrantClient(url=cluster_endpoint, api_key=api_key)

        # Test connection with a simple operation
        client.get_collections()
        print("✅ Client connected successfully")
        return client

    except Exception as e:
        print(f"❌ Failed to create Qdrant client: {e}")
        return None


def main():
    """Main latency measurement function."""
    print("=" * 60)
    print("CLI112C: Qdrant Cloud Latency Measurement")
    print("=" * 60)

    # Extract hostname from endpoint for ping
    endpoint_hostname = "ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io"

    print("🌍 Measuring latency from Vietnam to Qdrant Cloud (us-east4-0)")
    print(f"🎯 Target: {endpoint_hostname}")

    # Step 1: Measure ping latency
    print("\n1️⃣ Measuring ping latency...")
    ping_latency = measure_ping_latency(endpoint_hostname)

    if ping_latency is not None:
        log_result("Ping", ping_latency, "SUCCESS")
    else:
        log_result("Ping", 0.0, "FAILED")

    # Step 2: Get API key
    print("\n2️⃣ Retrieving API key...")
    api_key = get_api_key_from_secret_manager()
    if not api_key:
        print("❌ Cannot proceed with search test without API key")
        log_result("SimpleSearch", 0.0, "FAILED_NO_API_KEY")
        return

    # Step 3: Measure search latency
    print("\n3️⃣ Measuring search operation latency...")
    client = create_qdrant_client(api_key)
    if client:
        search_latency = measure_search_latency(client)

        if search_latency is not None:
            log_result("SimpleSearch", search_latency, "SUCCESS")
        else:
            log_result("SimpleSearch", 0.0, "FAILED")
    else:
        log_result("SimpleSearch", 0.0, "FAILED_NO_CLIENT")

    # Summary
    print("\n" + "=" * 60)
    print("📊 LATENCY MEASUREMENT SUMMARY")
    print("=" * 60)

    if ping_latency is not None:
        print(f"🏓 Ping latency: {ping_latency:.2f}ms")
    else:
        print("🏓 Ping latency: FAILED")

    if "search_latency" in locals() and search_latency is not None:
        print(f"🔍 Search latency: {search_latency:.2f}ms")
    else:
        print("🔍 Search latency: FAILED")

    print("📝 Results logged to: logs/latency_probe.log")
    print("🎯 Baseline latency measurement completed")


if __name__ == "__main__":
    main()
