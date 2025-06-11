from typing import Dict, Any, Optional
from collections import defaultdict


class FakeFirestoreDocument:
    def __init__(self, data: Dict[str, Any], id: str):
        self._data = data
        self.id = id

    def to_dict(self) -> Dict[str, Any]:
        return self._data


class FakeFirestoreCollection:
    def __init__(self, name: str):
        self.name = name
        self._documents = {}

    def document(self, doc_id: str):
        # Ensure that a document is returned even if it does not exist yet,
        # similar to Firestore's behavior.
        # The actual data fetching or creation happens with get() or set().
        if doc_id not in self._documents:
            # Firestore's document() method doesn't create the document in the backend
            # until set() or update() is called. It just returns a reference.
            # We simulate this by returning a document with empty data if not found.
            return FakeFirestoreDocument({}, doc_id)
        return FakeFirestoreDocument(self._documents.get(doc_id, {}), doc_id)

    def set(self, doc_id: str, data: Dict[str, Any]):
        self._documents[doc_id] = data
        return FakeFirestoreDocument(data, doc_id)

    def get(self, doc_id: str) -> Optional[FakeFirestoreDocument]:
        if doc_id in self._documents:
            return FakeFirestoreDocument(self._documents[doc_id], doc_id)
        return None

    def update(self, doc_id: str, data: Dict[str, Any]):
        if doc_id in self._documents:
            self._documents[doc_id].update(data)
        else:
            # Firestore's update() creates the document if it doesn't exist.
            self._documents[doc_id] = data
        return FakeFirestoreDocument(self._documents[doc_id], doc_id)

    def delete(self, doc_id: str):
        self._documents.pop(doc_id, None)


class FakeFirestoreClient:
    def __init__(self):
        self._collections = defaultdict(lambda: FakeFirestoreCollection(""))

    def collection(self, *collection_path: "str") -> "CollectionReference":
        """Match real Firestore client signature with *collection_path"""
        collection_name = "/".join(collection_path)
        # Ensure the collection name is set when it's first accessed or created.
        if collection_name not in self._collections:
            self._collections[collection_name] = FakeFirestoreCollection(collection_name)
        # Or, if it was created by defaultdict with an empty name, set it.
        elif not self._collections[collection_name].name:
            self._collections[collection_name].name = collection_name
        return self._collections[collection_name]

    # Add missing methods to match real FirestoreClient
    def _determine_default(self, *args, **kwargs):
        """Placeholder for _determine_default method"""
        return None

    def _document_path_helper(self, *args, **kwargs):
        """Placeholder for _document_path_helper method"""
        return ""

    def _emulator_channel(self, *args, **kwargs):
        """Placeholder for _emulator_channel method"""
        return None

    def _firestore_api_helper(self, *args, **kwargs):
        """Placeholder for _firestore_api_helper method"""
        return None

    def _get_collection_reference(self, *args, **kwargs):
        """Placeholder for _get_collection_reference method"""
        return None

    def _prep_collections(self, *args, **kwargs):
        """Placeholder for _prep_collections method"""
        return []

    def _prep_get_all(self, *args, **kwargs):
        """Placeholder for _prep_get_all method"""
        return []

    def _recursive_delete(self, *args, **kwargs):
        """Placeholder for _recursive_delete method"""
        return None

    def _target_helper(self, *args, **kwargs):
        """Placeholder for _target_helper method"""
        return None

    def batch(self, *args, **kwargs):
        """Placeholder for batch method"""
        return None

    def bulk_writer(self, *args, **kwargs):
        """Placeholder for bulk_writer method"""
        return None

    def close(self, *args, **kwargs):
        """Placeholder for close method"""
        pass

    def collection_group(self, *args, **kwargs):
        """Placeholder for collection_group method"""
        return None

    def collections(self, *args, **kwargs):
        """Placeholder for collections method"""
        return []

    def document(self, *args, **kwargs):
        """Placeholder for document method"""
        return None

    def field_path(self, *args, **kwargs):
        """Placeholder for field_path method"""
        return None

    def get_all(self, *args, **kwargs):
        """Placeholder for get_all method"""
        return []

    def recursive_delete(self, *args, **kwargs):
        """Placeholder for recursive_delete method"""
        return None

    def transaction(self, *args, **kwargs):
        """Placeholder for transaction method"""
        return None

    def write_option(self, *args, **kwargs):
        """Placeholder for write_option method"""
        return None

    def clear_all_data(self):
        """Clear all data from the fake Firestore client"""
        self._collections.clear()
