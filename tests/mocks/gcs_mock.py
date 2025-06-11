from typing import Dict, Optional
from io import BytesIO


class FakeGCSBlob:
    def __init__(self, name: str, data: bytes = None):
        self.name = name
        self._data = data or b""

    def upload_from_file(self, file_obj: BytesIO):
        self._data = file_obj.getvalue()

    def download_as_bytes(self) -> bytes:
        return self._data

    def delete(self):
        self._data = None


class FakeGCSBucket:
    def __init__(self, name: str):
        self.name = name
        self._blobs: Dict[str, FakeGCSBlob] = {}

    def blob(self, blob_name: str) -> FakeGCSBlob:
        if blob_name not in self._blobs:
            self._blobs[blob_name] = FakeGCSBlob(blob_name)
        return self._blobs[blob_name]

    def get_blob(self, blob_name: str) -> Optional[FakeGCSBlob]:
        return self._blobs.get(blob_name)

    def delete_blob(self, blob_name: str):
        self._blobs.pop(blob_name, None)


class FakeGCSClient:
    def __init__(self):
        self._buckets: Dict[str, FakeGCSBucket] = {}

    def bucket(self, bucket_name: str) -> FakeGCSBucket:
        if bucket_name not in self._buckets:
            self._buckets[bucket_name] = FakeGCSBucket(bucket_name)
        return self._buckets[bucket_name]

    def clear_all_data(self):
        self._buckets.clear()
