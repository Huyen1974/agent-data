import pytest
from fastapi.testclient import TestClient
from tests.mocks.gcs_mock import FakeGCSClient
from io import BytesIO


@pytest.fixture
def gcs_mock():
    client = FakeGCSClient()
    client.clear_all_data()
    yield client


@pytest.mark.unit
def test_upload_and_download_blob(gcs_mock, client_with_qdrant_override: TestClient):
    bucket_name = "test_bucket"
    blob_name = "test_blob.txt"
    content = b"Hello, GCS!"

    bucket = gcs_mock.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(BytesIO(content))

    retrieved_blob = bucket.get_blob(blob_name)
    assert retrieved_blob is not None, "Expected to retrieve blob"
    assert retrieved_blob.download_as_bytes() == content, "Downloaded content does not match uploaded"
