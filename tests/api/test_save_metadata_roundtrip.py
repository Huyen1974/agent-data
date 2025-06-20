import pytest
from fastapi.testclient import TestClient
from tests.mocks.firestore_fake import FakeFirestoreClient


@pytest.fixture
def firestore_mock():
    client = FakeFirestoreClient()
    client.clear_all_data()
    yield client


def test_save_metadata_roundtrip(firestore_mock, client_with_qdrant_override: TestClient):
    metadata = {"doc_id": "test_doc", "title": "Test Document", "status": "active"}
    collection = firestore_mock.collection("metadata")
    collection.set("test_doc", metadata)

    retrieved_doc = collection.get("test_doc")
    assert retrieved_doc is not None, "Expected to retrieve document"
    assert retrieved_doc.to_dict() == metadata, "Retrieved metadata does not match saved metadata"
