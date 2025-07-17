import logging
import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.agent_data_manager.vector_store.firestore_metadata_manager import (
    FirestoreMetadataManager,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CS Agent API",
    description="API for CS Agent Tree View and Search functionality",
    version="1.0.0",
)


# Pydantic models for Tree View endpoint
class TreeViewResponse(BaseModel):
    path: str | None = Field(None, description="Hierarchical path of the document")
    share_url: str | None = Field(None, description="Shareable URL for the document")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    status: str = Field(description="Response status")


# Pydantic models for Search endpoint
class SearchResponse(BaseModel):
    results: list[dict[str, Any]] = Field(
        default_factory=list, description="Search results"
    )
    total: int = Field(description="Total number of results")
    status: str = Field(description="Response status")


# Dependency to get FirestoreMetadataManager instance
def get_firestore_manager():
    """Get FirestoreMetadataManager instance."""
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "chatgpt-db-project")
    collection_name = os.environ.get("FIRESTORE_COLLECTION", "document_metadata")
    return FirestoreMetadataManager(
        project_id=project_id, collection_name=collection_name
    )


@app.get("/tree-view/{doc_id}", response_model=TreeViewResponse)
async def get_tree_view(
    doc_id: str,
    shared_by: str | None = Query(
        None, description="Email of user sharing the document"
    ),
    expires_days: int = Query(7, description="Number of days until share link expires"),
    firestore_manager: FirestoreMetadataManager = Depends(get_firestore_manager),
):
    """
    Get Tree View data for a document including path and share URL.

    Args:
        doc_id: Document identifier
        shared_by: Optional email of user sharing the document
        expires_days: Number of days until share link expires (default: 7)

    Returns:
        TreeViewResponse with path, share_url, and metadata
    """
    try:
        # Get document path
        path = await firestore_manager.get_document_path(doc_id)

        # Generate share link
        share_result = await firestore_manager.share_document(
            doc_id, shared_by=shared_by, expires_days=expires_days
        )

        # Get document metadata
        metadata = await firestore_manager.get_metadata_with_version(doc_id)

        if path is None and share_result is None and metadata is None:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        return TreeViewResponse(
            path=path,
            share_url=share_result.get("share_url") if share_result else None,
            metadata=metadata or {},
            status="ok",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting tree view for document {doc_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/search", response_model=SearchResponse)
async def search_documents(
    path: str | None = Query(None, description="Path segment to search for"),
    tags: str | None = Query(None, description="Comma-separated tags to search for"),
    metadata: str | None = Query(
        None, description="JSON string of metadata filters"
    ),
    firestore_manager: FirestoreMetadataManager = Depends(get_firestore_manager),
):
    """
    Search documents by path, tags, or metadata.

    Args:
        path: Path segment to search for (e.g., "research_paper")
        tags: Comma-separated tags to search for (e.g., "python,machine_learning")
        metadata: JSON string of metadata filters (e.g., '{"author": "John Doe", "year": 2024}')

    Returns:
        SearchResponse with results and total count
    """
    try:
        all_results = []

        # Search by path if provided
        if path and path.strip():
            path_results = await firestore_manager.search_by_path(path.strip())
            all_results.extend(path_results)

        # Search by tags if provided
        if tags and tags.strip():
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if tag_list:
                tag_results = await firestore_manager.search_by_tags(tag_list)
                # Avoid duplicates by checking doc_id
                existing_doc_ids = {result.get("_doc_id") for result in all_results}
                for result in tag_results:
                    if result.get("_doc_id") not in existing_doc_ids:
                        all_results.append(result)

        # Search by metadata if provided
        if metadata and metadata.strip():
            try:
                import json

                metadata_filters = json.loads(metadata.strip())
                if isinstance(metadata_filters, dict) and metadata_filters:
                    metadata_results = await firestore_manager.search_by_metadata(
                        metadata_filters
                    )
                    # Avoid duplicates by checking doc_id
                    existing_doc_ids = {result.get("_doc_id") for result in all_results}
                    for result in metadata_results:
                        if result.get("_doc_id") not in existing_doc_ids:
                            all_results.append(result)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, detail="Invalid JSON format for metadata parameter"
                )

        # If no search parameters provided, return empty results
        if not any([path, tags, metadata]):
            return SearchResponse(results=[], total=0, status="ok")

        return SearchResponse(results=all_results, total=len(all_results), status="ok")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "CS Agent API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
