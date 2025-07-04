import faiss
import numpy as np
import pytest
from agent_data.vector_store.qdrant_store import QdrantStore
from migration_cli import migrate_faiss_to_qdrant


@pytest.fixture
def faiss_index_file(tmp_path):
    """Create a small FAISS index for testing migration."""
    dimension = 128
    num_vectors = 5

    # Create a simple flat L2 index
    index = faiss.IndexFlatL2(dimension)

    # Generate random vectors
    vectors = np.random.random((num_vectors, dimension)).astype("float32")

    # Add vectors to index
    index.add(vectors)

    # Save index to temporary file
    index_path = str(tmp_path / "test_index.faiss")
    faiss.write_index(index, index_path)

    return index_path


    @pytest.mark.unitdef test_migration_smoke(faiss_index_file):
    """Smoke test for FAISS to Qdrant migration functionality."""
    collection_name = "test_collection_smoke"

    # Run migration
    result = migrate_faiss_to_qdrant(faiss_index_file, collection_name, batch_size=2)

    # Verify migration result
    assert result["status"] == "success"
    assert result["migrated_count"] == 5

    # Verify vectors were actually upserted to Qdrant
    qdrant_store = QdrantStore()
    count_response = qdrant_store.client.count(collection_name=collection_name)
    assert count_response.count == 5
