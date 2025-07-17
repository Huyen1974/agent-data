#!/usr/bin/env python3
"""
CLI112B: Qdrant Cluster Connectivity Verification Script

This script verifies:
1. Secret Manager API key accessibility
2. Qdrant cluster connectivity
3. Basic operations (list collections, get info)
"""

import subprocess
import sys

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException


def get_api_key_from_secret_manager():
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


def verify_qdrant_connectivity(api_key):
    """Verify connectivity to Qdrant cluster."""
    cluster_endpoint = (
        "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io"
    )
    cluster_id = "ba0aa7ef-be87-47b4-96de-7d36ca4527a8"

    try:
        print(f"🔗 Connecting to Qdrant cluster: {cluster_id}")
        print(f"📍 Endpoint: {cluster_endpoint}")

        client = QdrantClient(url=cluster_endpoint, api_key=api_key)

        # Test basic connectivity by getting collections info (simpler than cluster info)
        print("📦 Testing collections access...")
        collections = client.get_collections()
        print("✅ Collections retrieved successfully")

        print(f"📊 Total collections: {len(collections.collections)}")
        for collection in collections.collections:
            print(f"  - {collection.name}")

        # Test basic health check with a simple operation
        print("🏥 Testing cluster health...")
        try:
            # This should work even if no collections exist
            collection_info = client.get_collections()
            print("✅ Cluster is responsive and healthy")
        except Exception as e:
            print(f"⚠️  Health check warning: {e}")

        return True

    except ResponseHandlingException as e:
        print(f"❌ Qdrant API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def main():
    """Main verification function."""
    print("=" * 60)
    print("CLI112B: Qdrant Cluster Connectivity Verification")
    print("=" * 60)

    # Step 1: Verify Secret Manager access
    print("\n1️⃣ Verifying Secret Manager API key access...")
    api_key = get_api_key_from_secret_manager()
    if not api_key:
        print("❌ Cannot proceed without API key")
        sys.exit(1)

    # Step 2: Verify Qdrant connectivity
    print("\n2️⃣ Verifying Qdrant cluster connectivity...")
    success = verify_qdrant_connectivity(api_key)

    if success:
        print("\n✅ ALL VERIFICATIONS PASSED")
        print("🎯 Qdrant cluster is operational and ready for Agent Data development")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED")
        print("🚨 Qdrant cluster connectivity issues detected")
        sys.exit(1)


if __name__ == "__main__":
    main()
