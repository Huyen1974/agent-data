#!/usr/bin/env python3
"""Test script to verify metrics integration with Prometheus Pushgateway."""

import asyncio
import os
import sys

# Add ADK to path before importing modules
sys.path.insert(0, "ADK")

# Now import the ADK modules
from agent_data_manager.config.settings import settings
from agent_data_manager.tools.prometheus_metrics import get_metrics_summary
from agent_data_manager.vector_store.qdrant_store import QdrantStore


async def test_metrics_integration():
    """Test the metrics integration with QdrantStore."""
    print("🧪 Testing Metrics Integration with Prometheus Pushgateway")
    print("=" * 60)

    # Display configuration
    metrics_config = settings.get_metrics_config()
    qdrant_config = settings.get_qdrant_config()

    print("📊 Metrics Config:")
    print(f"   - Pushgateway URL: {metrics_config['pushgateway_url']}")
    print(f"   - Push Interval: {metrics_config['push_interval']}s")
    print(f"   - Enabled: {metrics_config['enabled']}")
    print()

    print("🔗 Qdrant Config:")
    print(f"   - URL: {qdrant_config['url']}")
    print(f"   - Collection: {qdrant_config['collection_name']}")
    print(f"   - Vector Size: {qdrant_config['vector_size']}")
    print()

    # Initialize QdrantStore (this should start metrics pusher)
    print("🚀 Initializing QdrantStore...")
    try:
        store = QdrantStore(
            url=qdrant_config["url"],
            api_key=qdrant_config["api_key"],
            collection_name=qdrant_config["collection_name"],
            vector_size=qdrant_config["vector_size"],
        )
        print("✅ QdrantStore initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize QdrantStore: {e}")
        return False

    # Wait a moment for metrics pusher to start
    await asyncio.sleep(2)

    # Check metrics summary
    print("\n📈 Metrics Summary:")
    summary = get_metrics_summary()
    for key, value in summary.items():
        print(f"   - {key}: {value}")
    print()

    # Test some operations to generate metrics
    print("🔄 Testing operations to generate metrics...")

    # Test health check
    print("   1. Health check...")
    healthy = await store.health_check()
    print(f"      Result: {'✅ Healthy' if healthy else '❌ Unhealthy'}")

    # Test vector count
    print("   2. Getting vector count...")
    count = await store.get_vector_count()
    print(f"      Count: {count} vectors")

    # Test upsert
    print("   3. Upserting test vector...")
    test_vector = [0.1] * qdrant_config["vector_size"]
    result = await store.upsert_vector(
        vector_id="test_metrics_vector",
        vector=test_vector,
        metadata={"test": "metrics"},
        tag="test_metrics",
    )
    print(f"      Result: {'✅ Success' if result.get('success') else '❌ Failed'}")

    # Test query
    print("   4. Querying by tag...")
    query_results = await store.query_vectors_by_tag("test_metrics", limit=1)
    print(f"      Found: {len(query_results)} vectors")

    print("\n⏱️  Waiting 65 seconds to observe metrics push...")
    print("   (This allows time for one metrics push cycle)")

    # Wait for metrics to be pushed
    for i in range(65, 0, -5):
        print(f"   ⏳ {i}s remaining...", end="\r")
        await asyncio.sleep(5)

    print("\n✅ Test completed! Check Cloud Monitoring for metrics.")
    print("\n📝 Expected metrics in Cloud Monitoring:")
    print("   - qdrant_requests_total")
    print("   - qdrant_request_duration_seconds")
    print("   - qdrant_connection_status")
    print("   - qdrant_vector_count")
    print("   - semantic_searches_total")

    return True


if __name__ == "__main__":
    # Set up test environment variables if not set
    if not os.environ.get("QDRANT_API_KEY"):
        print("⚠️  Warning: QDRANT_API_KEY not set. Using test mode.")
        # In real deployment, this would be set from Secret Manager

    if not os.environ.get("PUSHGATEWAY_URL"):
        # Use the deployed Pushgateway URL
        os.environ["PUSHGATEWAY_URL"] = "https://prometheus-pushgateway-812872501910.asia-southeast1.run.app"

    # Run the test
    asyncio.run(test_metrics_integration())
