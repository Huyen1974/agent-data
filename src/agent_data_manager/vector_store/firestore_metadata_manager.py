"""Stub module for FirestoreMetadataManager to allow test collection."""

from typing import Dict, List, Any, Optional


class FirestoreMetadataManager:
    """Stub FirestoreMetadataManager for test collection."""
    
    def __init__(self, project_id: str = None, collection_name: str = None):
        self.project_id = project_id
        self.collection_name = collection_name
        self.db = None
    
    async def get_document_path(self, point_id: str) -> Optional[str]:
        """Stub method for getting document path."""
        return f"mock/path/{point_id}"
    
    async def share_document(self, point_id: str, shared_by: str = None, expires_days: int = 7) -> Dict[str, Any]:
        """Stub method for sharing documents."""
        return {
            "share_id": "mock-share-id",
            "share_url": f"https://mock.com/share/{point_id}",
            "doc_id": point_id,
            "shared_by": shared_by,
            "expires_days": expires_days
        }
    
    async def get_metadata_with_version(self, point_id: str) -> Optional[Dict[str, Any]]:
        """Stub method for getting metadata."""
        return {
            "doc_id": point_id,
            "version": 1,
            "lastUpdated": "2024-01-01T00:00:00Z"
        }
    
    async def search_by_path(self, path: str) -> List[Dict[str, Any]]:
        """Stub method for path search."""
        return []
    
    async def search_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Stub method for tags search."""
        return []
    
    async def search_by_metadata(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stub method for metadata search."""
        return []
    
    async def query_by_hierarchy_optimized(self, **kwargs) -> List[Dict[str, Any]]:
        """Stub method for optimized hierarchy query."""
        return []
    
    async def query_by_version_range_optimized(self, **kwargs) -> List[Dict[str, Any]]:
        """Stub method for optimized version range query."""
        return []
    
    async def query_latest_by_category_optimized(self, **kwargs) -> List[Dict[str, Any]]:
        """Stub method for optimized latest by category query."""
        return []
    
    async def query_multi_level_hierarchy_optimized(self, **kwargs) -> List[Dict[str, Any]]:
        """Stub method for optimized multi-level hierarchy query."""
        return []
    
    async def _check_document_exists(self, doc_ref) -> bool:
        """Stub method for checking document existence."""
        return True
    
    async def _get_document_for_versioning(self, doc_ref):
        """Stub method for getting document for versioning."""
        class MockDocSnapshot:
            exists = False
            def to_dict(self):
                return {"version": 1, "lastUpdated": "2024-01-01T00:00:00Z"}
        return MockDocSnapshot()
