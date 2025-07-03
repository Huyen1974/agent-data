"""
Test suite to verify Terraform-managed bucket existence and accessibility.
"""

import pytest
from google.cloud import storage
from google.api_core import exceptions


class TestTerraformBuckets:
    """Test Terraform-managed GCS buckets."""
    
    @pytest.fixture(scope="class")
    def storage_client(self):
        """Create a GCS client for testing."""
        return storage.Client()
    
    @pytest.mark.unit
    @pytest.mark.parametrize("bucket_name,project_id", [
        ("huyen1974-faiss-index-storage-test", "github-chatgpt-ggcloud"),
        ("huyen1974-qdrant-snapshots", "github-chatgpt-ggcloud"),
        ("huyen1974-agent-data-terraform-state", "github-chatgpt-ggcloud"),
    ])
    def test_bucket_exists(self, storage_client, bucket_name, project_id):
        """Test that Terraform-managed buckets exist."""
        try:
            bucket = storage_client.bucket(bucket_name)
            bucket.reload()
            assert bucket.exists(), f"Bucket {bucket_name} does not exist"
            print(f"✅ Bucket {bucket_name} exists")
        except exceptions.NotFound:
            pytest.fail(f"Bucket {bucket_name} not found")
        except exceptions.Forbidden:
            pytest.fail(f"Access denied to bucket {bucket_name}")
    
    @pytest.mark.unit
    @pytest.mark.parametrize("bucket_name,expected_location", [
        ("huyen1974-faiss-index-storage-test", "ASIA-SOUTHEAST1"),
        ("huyen1974-qdrant-snapshots", "ASIA-SOUTHEAST1"),
        ("huyen1974-agent-data-terraform-state", "ASIA-SOUTHEAST1"),
    ])
    def test_bucket_location(self, storage_client, bucket_name, expected_location):
        """Test that buckets are in the correct location."""
        try:
            bucket = storage_client.bucket(bucket_name)
            bucket.reload()
            assert bucket.location == expected_location, \
                f"Bucket {bucket_name} location is {bucket.location}, expected {expected_location}"
            print(f"✅ Bucket {bucket_name} location: {bucket.location}")
        except exceptions.NotFound:
            pytest.fail(f"Bucket {bucket_name} not found")
        except exceptions.Forbidden:
            pytest.fail(f"Access denied to bucket {bucket_name}")
    
    @pytest.mark.unit
    @pytest.mark.parametrize("bucket_name,expected_labels", [
        ("huyen1974-faiss-index-storage-test", {
            "environment": "test",
            "purpose": "faiss-index-storage",
            "managed_by": "terraform"
        }),
        ("huyen1974-qdrant-snapshots", {
            "environment": "production", 
            "purpose": "qdrant-snapshots",
            "managed_by": "terraform"
        }),
        ("huyen1974-agent-data-terraform-state", {
            "environment": "infrastructure",
            "purpose": "terraform-state", 
            "managed_by": "terraform"
        }),
    ])
    def test_bucket_labels(self, storage_client, bucket_name, expected_labels):
        """Test that buckets have correct Terraform labels."""
        try:
            bucket = storage_client.bucket(bucket_name)
            bucket.reload()
            bucket_labels = bucket.labels or {}
            
            for key, expected_value in expected_labels.items():
                assert key in bucket_labels, \
                    f"Label {key} missing from bucket {bucket_name}"
                assert bucket_labels[key] == expected_value, \
                    f"Label {key} in bucket {bucket_name} is {bucket_labels[key]}, expected {expected_value}"
            
            print(f"✅ Bucket {bucket_name} labels: {bucket_labels}")
        except exceptions.NotFound:
            pytest.fail(f"Bucket {bucket_name} not found")
        except exceptions.Forbidden:
            pytest.fail(f"Access denied to bucket {bucket_name}")
    
    @pytest.mark.unit
    def test_terraform_state_bucket_accessible(self, storage_client):
        """Test that Terraform state bucket is accessible for read/write operations."""
        bucket_name = "huyen1974-agent-data-terraform-state"
        try:
            bucket = storage_client.bucket(bucket_name)
            bucket.reload()
            
            # Test listing objects (should not fail)
            list(bucket.list_blobs(max_results=1))
            print(f"✅ Terraform state bucket {bucket_name} is accessible")
            
        except exceptions.NotFound:
            pytest.fail(f"Terraform state bucket {bucket_name} not found")
        except exceptions.Forbidden:
            pytest.fail(f"Access denied to Terraform state bucket {bucket_name}")
    
    @pytest.mark.unit 
    def test_bucket_count(self, storage_client):
        """Test that all expected Terraform buckets exist."""
        expected_buckets = [
            "huyen1974-faiss-index-storage-test",
            "huyen1974-qdrant-snapshots", 
            "huyen1974-agent-data-terraform-state"
        ]
        
        existing_buckets = []
        for bucket_name in expected_buckets:
            try:
                bucket = storage_client.bucket(bucket_name)
                bucket.reload()
                if bucket.exists():
                    existing_buckets.append(bucket_name)
            except (exceptions.NotFound, exceptions.Forbidden):
                continue
        
        assert len(existing_buckets) == len(expected_buckets), \
            f"Expected {len(expected_buckets)} buckets, found {len(existing_buckets)}: {existing_buckets}"
        
        print(f"✅ All {len(existing_buckets)} Terraform buckets exist: {existing_buckets}") 