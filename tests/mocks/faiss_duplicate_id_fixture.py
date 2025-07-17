import faiss
import numpy as np
import pytest


@pytest.fixture
def faiss_index_with_duplicates(tmp_path):
    dimension = 1536
    # Use IndexIDMap to allow custom IDs, including duplicates
    base_index = faiss.IndexFlatL2(dimension)
    index = faiss.IndexIDMap(base_index)
    vectors = np.random.random((10, dimension)).astype("float32")
    # Add vectors with duplicate IDs by manipulating index
    index.add_with_ids(vectors[:5], np.array([0, 1, 2, 3, 4], dtype=np.int64))
    index.add_with_ids(
        vectors[5:], np.array([2, 3, 4, 5, 6], dtype=np.int64)
    )  # Duplicate IDs 2, 3, 4
    index_path = str(tmp_path / "dup_id_index.faiss")
    faiss.write_index(index, index_path)
    payloads = [{"id": i, "text": f"doc_{i}"} for i in [0, 1, 2, 3, 4, 2, 3, 4, 5, 6]]
    return {"index_path": index_path, "payloads": payloads}
