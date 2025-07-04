"""
CLI 126B: Test cases for mocking and caching implementation
Validates that external services are properly mocked and embeddings are cached.
"""

import pytest
import json
from pathlib import Path


class TestCLI126BMocking:
    """Test cases for CLI 126B mocking and caching functionality."""

    @pytest.mark.unit    def test_qdrant_mock_functionality(self, qdrant_cloud_mock):
        """Test that Qdrant mock returns expected responses."""
        # Test get_collections
        collections = qdrant_cloud_mock.get_collections()
        assert hasattr(collections, "collections")
        assert len(collections.collections) == 2
        assert collections.collections[0].name == "my_collection"
        assert collections.collections[0].vectors_count == 100

        # Test get_collection
        collection_info = qdrant_cloud_mock.get_collection("test_collection")
        assert collection_info.status == "green"
        assert collection_info.vectors_count == 100
        assert collection_info.config.params.vectors.size == 1536

        # Test upsert
        upsert_result = qdrant_cloud_mock.upsert(
            collection_name="test_collection",
            points=[{"id": 1, "vector": [0.1] * 1536, "payload": {"test": True}}],
        )
        assert upsert_result.status == "completed"
        assert hasattr(upsert_result, "operation_id")

        # Test search
        search_results = qdrant_cloud_mock.search(collection_name="test_collection", query_vector=[0.1] * 1536, limit=2)
        assert len(search_results) == 2
        assert search_results[0].score == 0.92
        assert search_results[0].payload["tag"] == "science"

    @pytest.mark.unit    def test_openai_mock_functionality(self, openai_mock):
        """Test that OpenAI mock returns static embeddings."""
        # Test embedding creation
        response = openai_mock.embeddings.create(input="test text for embedding", model="text-embedding-ada-002")

        assert hasattr(response, "data")
        assert len(response.data) == 1
        assert len(response.data[0].embedding) == 1536

        # Test that same input produces same embedding (deterministic)
        response2 = openai_mock.embeddings.create(input="test text for embedding", model="text-embedding-ada-002")

        assert response.data[0].embedding == response2.data[0].embedding

    @pytest.mark.unit    def test_embedding_cache_functionality(self, openai_embedding_cache):
        """Test that cached embeddings are used instead of generating new ones."""
        test_text = "This is a test sentence for caching"

        # First call should generate and cache embedding
        embedding1 = openai_embedding_cache(test_text)
        assert len(embedding1) == 1536
        assert all(isinstance(x, float) for x in embedding1)
        assert all(-1.0 <= x <= 1.0 for x in embedding1)

        # Second call should return cached embedding
        embedding2 = openai_embedding_cache(test_text)
        assert embedding1 == embedding2

        # Different text should produce different embedding
        embedding3 = openai_embedding_cache("Different text")
        assert embedding1 != embedding3

        # Check that cache file exists
        cache_file = Path(".cache/test_embeddings.json")
        assert cache_file.exists()

        # Verify cache contents
        with open(cache_file, "r") as f:
            cache_data = json.load(f)

        cache_key1 = f"text-embedding-ada-002:{test_text}"
        cache_key2 = "text-embedding-ada-002:Different text"

        assert cache_key1 in cache_data
        assert cache_key2 in cache_data
        assert cache_data[cache_key1] == embedding1
        assert cache_data[cache_key2] == embedding3

    @pytest.mark.unit    def test_fast_e2e_mocks_integration(self, fast_e2e_mocks):
        """Test that the combined E2E mocks provide realistic responses."""
        mocks = fast_e2e_mocks

        # Test Qdrant client mock
        qdrant_client = mocks["qdrant_client"]
        collections = qdrant_client.get_collections()
        assert len(collections.collections) == 2

        # Test OpenAI client mock
        openai_client = mocks["openai_client"]
        response = openai_client.embeddings.create(input="test integration text", model="text-embedding-ada-002")
        assert len(response.data[0].embedding) == 1536

        # Test GCS client mock
        gcs_client = mocks["gcs_client"]
        bucket = gcs_client.bucket("test-bucket")
        blob = bucket.blob("test-file.txt")
        blob.upload_from_string("test content")
        content = blob.download_as_text()
        assert content == "Test content"

        # Test Firestore client mock
        firestore_client = mocks["firestore_client"]
        collection = firestore_client.collection("test_collection")
        doc_ref = collection.document("test_doc")
        doc_ref.set({"data": "test"})
        # Just verify the mock methods exist and are callable
        assert hasattr(doc_ref, "set")
        assert hasattr(doc_ref, "get")
        assert hasattr(doc_ref, "update")

        # Test embedding cache
        embedding_cache = mocks["embedding_cache"]
        embedding = embedding_cache("integration test text")
        assert len(embedding) == 1536

    @pytest.mark.unit    def test_auto_mock_external_services(self):
        """Test that external services are automatically mocked by default."""
        # This test runs without explicit fixtures to verify auto-mocking

        # Test that importing external clients doesn't fail
        try:
            from qdrant_client import QdrantClient
            from openai import OpenAI

            # Create clients (should be mocked)
            qdrant_client = QdrantClient(url="http://test:6333", api_key="test")
            openai_client = OpenAI(api_key="test")

            # Test basic operations don't make real API calls
            collections = qdrant_client.get_collections()
            assert collections is not None

            response = openai_client.embeddings.create(input="auto mock test", model="text-embedding-ada-002")
            assert response is not None

        except ImportError:
            # Skip if libraries not available
            pytest.skip("External libraries not available for auto-mock test")

    @pytest.mark.unit    def test_mocking_performance_improvement(self, openai_embedding_cache):
        """Test that mocking provides performance improvement over real API calls."""
        import time

        # Test multiple embedding calls with caching
        test_texts = [
            "Performance test text 1",
            "Performance test text 2",
            "Performance test text 3",
            "Performance test text 1",  # Repeat to test caching
            "Performance test text 2",  # Repeat to test caching
        ]

        start_time = time.time()

        embeddings = []
        for text in test_texts:
            embedding = openai_embedding_cache(text)
            embeddings.append(embedding)

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete very quickly with caching
        assert total_time < 1.0, f"Cached embeddings took too long: {total_time}s"

        # Verify repeated texts return same embeddings
        assert embeddings[0] == embeddings[3]  # Same text 1
        assert embeddings[1] == embeddings[4]  # Same text 2

        # Verify different texts return different embeddings
        assert embeddings[0] != embeddings[1]
        assert embeddings[1] != embeddings[2]

    @pytest.mark.unit    def test_cache_persistence(self, openai_embedding_cache):
        """Test that embedding cache persists across test runs."""
        cache_file = Path(".cache/test_embeddings.json")
        test_text = "Persistence test text"

        # Generate embedding
        embedding1 = openai_embedding_cache(test_text)

        # Verify cache file was created/updated
        assert cache_file.exists()

        # Read cache directly
        with open(cache_file, "r") as f:
            cache_data = json.load(f)

        cache_key = f"text-embedding-ada-002:{test_text}"
        assert cache_key in cache_data
        assert cache_data[cache_key] == embedding1

        # Simulate fresh start by creating new cache function
        def fresh_cache_function(text: str, model: str = "text-embedding-ada-002") -> list:
            """Fresh cache function that should load existing cache."""

            cache = {}
            if cache_file.exists():
                try:
                    with open(cache_file, "r") as f:
                        cache = json.load(f)
                except (json.JSONDecodeError, IOError):
                    cache = {}

            cache_key = f"{model}:{text}"
            if cache_key in cache:
                return cache[cache_key]

            # This shouldn't be reached for our test text
            pytest.fail("Cache should have contained the test text")

        # Test that fresh function can load existing cache
        embedding2 = fresh_cache_function(test_text)
        assert embedding1 == embedding2
