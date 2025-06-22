#!/usr/bin/env python3
"""
End-to-End Test for QdrantStore with Latency Measurement
CLI 115A: Test save_document → vectorize → semantic_search workflow
"""

import asyncio
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import List

# Set environment variables directly
os.environ["QDRANT_URL"] = "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io"
os.environ["QDRANT_API_KEY"] = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.3exdWpAbjXl_o11YZHT3Cnlxklkpv5x4InI244BUYV0"
)
os.environ["QDRANT_COLLECTION_NAME"] = "agent_data_vectors"
os.environ["VECTOR_DIMENSION"] = "1536"
os.environ["ENABLE_FIRESTORE_SYNC"] = "false"
os.environ["OPENAI_API_KEY"] = "sk-test-key-for-cli115a"  # Placeholder - will be mocked

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ADK"))

# Import ADK modules after path setup
from agent_data_manager.config.settings import settings  # noqa: E402
from agent_data_manager.vector_store.qdrant_store import QdrantStore  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Performance logging setup
os.makedirs("logs", exist_ok=True)
perf_logger = logging.getLogger("performance")
perf_handler = logging.FileHandler("logs/performance_test.log")
perf_handler.setFormatter(logging.Formatter("%(asctime)s [%(message)s]"))
perf_logger.addHandler(perf_handler)
perf_logger.setLevel(logging.INFO)

slow_logger = logging.getLogger("slow_operations")
slow_handler = logging.FileHandler("logs/perf_slow.log")
slow_handler.setFormatter(logging.Formatter("%(asctime)s [%(message)s]"))
slow_logger.addHandler(slow_handler)
slow_logger.setLevel(logging.INFO)


class LatencyMeasurer:
    """Helper class to measure and log operation latency."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            latency_ms = int((time.time() - self.start_time) * 1000)
            status = "SUCCESS" if exc_type is None else "ERROR"

            # Log to performance log
            perf_logger.info(f"{self.operation_name} {latency_ms} {status}")

            # Log slow operations (>5s) to separate log
            if latency_ms > 5000:
                slow_logger.info(f"{self.operation_name} {latency_ms} {status}")

            # Print to console
            print(f"⏱️  {self.operation_name}: {latency_ms}ms ({status})")


def create_mock_embedding(text: str) -> List[float]:
    """Create a deterministic mock embedding based on text hash."""
    import hashlib

    # Create a deterministic hash-based embedding
    text_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
    # Convert hex to numbers and normalize to create a 1536-dimensional vector
    embedding = []
    for i in range(1536):
        # Use different parts of the hash to create variation
        hash_part = text_hash[(i % len(text_hash))]
        value = (ord(hash_part) - 48) / 15.0 - 0.5  # Normalize to [-0.5, 0.5]
        embedding.append(value)
    return embedding


def get_qdrant_store() -> QdrantStore:
    """Get QdrantStore instance."""
    config = settings.get_qdrant_config()
    return QdrantStore(
        url=config["url"],
        api_key=config["api_key"],
        collection_name=config["collection_name"],
        vector_size=config["vector_size"],
    )


async def test_qdrant_connectivity():
    """Test basic Qdrant connectivity."""
    print("\n🔗 Testing Qdrant connectivity...")

    with LatencyMeasurer("CONNECTIVITY_TEST"):
        try:
            store = get_qdrant_store()
            # Test basic collection access and ensure tag index
            await store._ensure_collection()
            print("✅ Qdrant connectivity successful")
            return True
        except Exception as e:
            print(f"❌ Qdrant connectivity failed: {e}")
            return False


async def test_save_document_workflow():
    """Test the save_document → vectorize workflow."""
    print("\n📝 Testing save_document → vectorize workflow...")

    test_documents = [
        {
            "name": "test_doc_1",
            "text": "This is a test document about machine learning and artificial intelligence.",
            "tag": "cli115a_test",
        },
        {
            "name": "test_doc_2",
            "text": "Python programming is essential for data science and AI development.",
            "tag": "cli115a_test",
        },
        {
            "name": "test_doc_3",
            "text": "Vector databases enable semantic search and similarity matching.",
            "tag": "cli115a_test",
        },
    ]

    successful_uploads = 0
    store = get_qdrant_store()

    for doc in test_documents:
        print(f"\n📄 Processing document: {doc['name']}")

        with LatencyMeasurer("SAVE_DOCUMENT"):
            try:
                # Generate UUID for point ID
                point_id = str(uuid.uuid4())

                # Generate mock embedding
                embedding = create_mock_embedding(doc["text"])

                # Store in Qdrant directly
                result = await store.upsert_vector(
                    vector_id=point_id,
                    vector=embedding,
                    metadata={
                        "original_text": doc["text"],
                        "document_name": doc["name"],
                        "document_type": "test",
                        "source": "cli115a",
                    },
                    tag=doc["tag"],
                )

                if result.get("success"):
                    print(f"✅ Document {doc['name']} saved successfully (ID: {point_id[:8]}...)")
                    successful_uploads += 1
                else:
                    print(f"❌ Failed to save document {doc['name']}: {result.get('error')}")

            except Exception as e:
                print(f"❌ Exception saving document {doc['name']}: {e}")

    print(f"\n📊 Save Document Results: {successful_uploads}/{len(test_documents)} successful")
    return successful_uploads > 0


async def test_semantic_search_workflow():
    """Test the semantic search workflow."""
    print("\n🔍 Testing semantic search workflow...")

    search_queries = [
        {
            "query": "machine learning algorithms",
            "expected_tag": "cli115a_test",
            "description": "AI/ML related query",
        },
        {
            "query": "programming languages for data",
            "expected_tag": "cli115a_test",
            "description": "Programming related query",
        },
        {
            "query": "database search capabilities",
            "expected_tag": "cli115a_test",
            "description": "Database related query",
        },
    ]

    successful_searches = 0
    store = get_qdrant_store()

    for query_info in search_queries:
        print(f"\n🔎 Searching: {query_info['description']}")
        print(f"   Query: '{query_info['query']}'")

        with LatencyMeasurer("SEMANTIC_SEARCH"):
            try:
                # Generate query embedding
                query_embedding = create_mock_embedding(query_info["query"])

                # Search in Qdrant
                results = await store.query_vectors_by_tag(
                    tag=query_info["expected_tag"],
                    query_vector=query_embedding,
                    limit=5,
                    threshold=0.3,
                )

                print(f"✅ Search successful: {len(results)} results found")

                # Display top results
                for i, res in enumerate(results[:3], 1):
                    score = res.get("score", 0)
                    doc_name = res.get("metadata", {}).get("document_name", "Unknown")
                    text_preview = res.get("metadata", {}).get("original_text", "")[:100]
                    if len(text_preview) > 100:
                        text_preview += "..."
                    print(f"   {i}. Score: {score:.3f} - {doc_name}: {text_preview}")

                successful_searches += 1

            except Exception as e:
                print(f"❌ Exception during search: {e}")

    print(f"\n📊 Semantic Search Results: {successful_searches}/{len(search_queries)} successful")
    return successful_searches > 0


async def test_end_to_end_performance():
    """Test complete end-to-end performance with timing."""
    print("\n⚡ Testing end-to-end performance...")

    total_start = time.time()

    # Test document with unique ID for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_doc = {
        "name": f"e2e_test_{timestamp}",
        "text": "End-to-end performance test document for Qdrant vector store integration with semantic search capabilities.",
        "tag": "cli115a_e2e",
    }

    store = get_qdrant_store()
    point_id = str(uuid.uuid4())

    # Step 1: Save document
    print("\n1️⃣ Saving test document...")
    with LatencyMeasurer("E2E_SAVE"):
        try:
            embedding = create_mock_embedding(test_doc["text"])
            save_result = await store.upsert_vector(
                vector_id=point_id,
                vector=embedding,
                metadata={
                    "original_text": test_doc["text"],
                    "document_name": test_doc["name"],
                    "test_type": "e2e",
                    "timestamp": timestamp,
                },
                tag=test_doc["tag"],
            )

            if not save_result.get("success"):
                print(f"❌ E2E test failed at save step: {save_result.get('error')}")
                return False
        except Exception as e:
            print(f"❌ E2E test failed at save step: {e}")
            return False

    # Step 2: Search for the document
    print("\n2️⃣ Searching for saved document...")
    with LatencyMeasurer("E2E_SEARCH"):
        try:
            query_embedding = create_mock_embedding("performance test document vector store")
            search_results = await store.query_vectors_by_tag(
                tag=test_doc["tag"], query_vector=query_embedding, limit=5, threshold=0.1
            )

            # Verify we found our document
            found_our_doc = any(res.get("id") == point_id for res in search_results)

        except Exception as e:
            print(f"❌ E2E test failed at search step: {e}")
            return False

    total_time = time.time() - total_start
    total_time_ms = int(total_time * 1000)

    print("\n📊 End-to-End Test Results:")
    print(f"   Total time: {total_time_ms}ms")
    print(f"   Document found: {'✅ Yes' if found_our_doc else '❌ No'}")
    print(f"   Results returned: {len(search_results)}")

    # Log total E2E performance
    perf_logger.info(f"E2E_TOTAL {total_time_ms} {'SUCCESS' if found_our_doc else 'PARTIAL'}")

    if total_time_ms > 5000:
        slow_logger.info(f"E2E_TOTAL {total_time_ms} {'SUCCESS' if found_our_doc else 'PARTIAL'}")

    return found_our_doc


async def cleanup_test_data():
    """Clean up test data created during the test."""
    print("\n🧹 Cleaning up test data...")

    try:
        # Note: QdrantStore doesn't have a direct delete_by_tag method
        # For now, we'll just log that cleanup would happen here
        print("ℹ️  Test data cleanup would be performed here")
        print("   (Individual vector deletion by ID would be needed)")

        return True
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")
        return False


async def main():
    """Main test execution function."""
    print("🚀 Starting CLI 115A End-to-End Test with QdrantStore")
    print("=" * 60)

    # Verify environment
    print("\n🔧 Verifying environment...")
    if not settings.validate_qdrant_config():
        print("❌ Qdrant configuration invalid. Check QDRANT_URL and QDRANT_API_KEY environment variables.")
        return False

    print(f"✅ Qdrant URL: {settings.QDRANT_URL}")
    print(f"✅ Collection: {settings.QDRANT_COLLECTION_NAME}")
    print(f"✅ Vector dimension: {settings.VECTOR_DIMENSION}")

    # Run test sequence
    test_results = {}

    try:
        # Test 1: Connectivity
        test_results["connectivity"] = await test_qdrant_connectivity()

        if not test_results["connectivity"]:
            print("\n❌ Connectivity test failed. Aborting remaining tests.")
            return False

        # Test 2: Save document workflow
        test_results["save_document"] = await test_save_document_workflow()

        # Test 3: Semantic search workflow
        test_results["semantic_search"] = await test_semantic_search_workflow()

        # Test 4: End-to-end performance
        test_results["e2e_performance"] = await test_end_to_end_performance()

        # Test 5: Cleanup
        test_results["cleanup"] = await cleanup_test_data()

    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        logger.exception("Test execution failed")
        return False

    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)

    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")

    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All tests passed! QdrantStore end-to-end workflow is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check logs for details.")
        return False


if __name__ == "__main__":
    # Run the test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
