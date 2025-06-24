from migrate_faiss_to_qdrant import migrate_faiss_to_qdrant

from tests.mocks.qdrant_basic import FakeQdrantClient
import pytest


def test_migration_handles_duplicate_ids(faiss_index_with_duplicates):
    client = FakeQdrantClient(url="http://mock-qdrant:6333")
    index_path = faiss_index_with_duplicates["index_path"]
    payloads = faiss_index_with_duplicates["payloads"]

    stats = migrate_faiss_to_qdrant(
        faiss_index_path=index_path,
        qdrant_client=client,
        collection_name="test_collection",
        payloads=payloads,
        dry_run=True,
    )

    assert stats["vectors_processed"] == 10, "Expected 10 vectors processed"
    assert stats["errors"] == 0, "Expected no errors with duplicate IDs"
    assert stats["skipped"] == 0, "Expected no skipped vectors"
    assert "error_message" not in stats, "Expected no error message in dry-run"
