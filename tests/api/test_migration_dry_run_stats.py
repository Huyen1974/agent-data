import pytest
import faiss
import numpy as np

from migrate_faiss_to_qdrant import migrate_faiss_to_qdrant

from tests.mocks.qdrant_basic import FakeQdrantClient


@pytest.fixture
def faiss_index(tmp_path):
    dimension = 1536
    index = faiss.IndexFlatL2(dimension)
    vectors = np.random.random((10, dimension)).astype("float32")
    index.add(vectors)
    index_path = str(tmp_path / "test_index.faiss")
    faiss.write_index(index, index_path)
    return index_path


def test_migration_dry_run_stats(faiss_index):
    client = FakeQdrantClient(url="http://mock-qdrant:6333")
    payloads = [{"id": i, "text": f"doc_{i}"} for i in range(10)]

    stats = migrate_faiss_to_qdrant(
        faiss_index_path=faiss_index,
        qdrant_client=client,
        collection_name="test_collection",
        payloads=payloads,
        dry_run=True,
    )

    assert stats["vectors_processed"] == 10, "Expected 10 vectors processed"
    assert stats["errors"] == 0, "Expected no errors"
    assert stats["skipped"] == 0, "Expected no skipped vectors"
    assert "error_message" not in stats, "Expected no error message in dry-run"
