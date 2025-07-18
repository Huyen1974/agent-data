"""Auto-tagging tool with OpenAI integration and Firestore caching for Agent Data system."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from ..config.settings import settings
from ..vector_store.firestore_metadata_manager import FirestoreMetadataManager
from .external_tool_registry import OPENAI_AVAILABLE, openai_client

logger = logging.getLogger(__name__)


class AutoTaggingTool:
    """Tool for generating intelligent tags using OpenAI API with Firestore caching."""

    def __init__(self):
        """Initialize the auto-tagging tool."""
        self.firestore_manager = None
        self.cache_collection = "auto_tag_cache"
        self.cache_ttl_hours = 24  # Cache tags for 24 hours
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure FirestoreMetadataManager is initialized."""
        if self._initialized:
            return

        try:
            # Initialize FirestoreMetadataManager for caching
            firestore_config = settings.get_firestore_config()
            self.firestore_manager = FirestoreMetadataManager(
                project_id=firestore_config.get("project_id"),
                collection_name=self.cache_collection,
            )
            self._initialized = True
            logger.info("AutoTaggingTool initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AutoTaggingTool: {e}")
            raise

    def _generate_content_hash(self, content: str) -> str:
        """
        Generate a hash for content to use as cache key.

        Args:
            content: Document content

        Returns:
            SHA256 hash of the content
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _get_cached_tags(self, content_hash: str) -> dict[str, Any] | None:
        """
        Retrieve cached tags from Firestore.

        Args:
            content_hash: Hash of the content

        Returns:
            Cached tag data or None if not found/expired
        """
        try:
            if not self.firestore_manager or not self.firestore_manager.db:
                return None

            doc_ref = self.firestore_manager.db.collection(
                self.cache_collection
            ).document(content_hash)
            doc = await doc_ref.get()

            if not doc.exists:
                return None

            data = doc.to_dict()

            # Check if cache is expired
            cached_time = datetime.fromisoformat(data.get("cached_at", ""))
            if datetime.utcnow() - cached_time > timedelta(hours=self.cache_ttl_hours):
                # Cache expired, delete it
                await doc_ref.delete()
                return None

            return data

        except Exception as e:
            logger.error(f"Failed to get cached tags: {e}")
            return None

    async def _cache_tags(
        self, content_hash: str, tags: list[str], metadata: dict[str, Any]
    ) -> None:
        """
        Cache generated tags in Firestore.

        Args:
            content_hash: Hash of the content
            tags: Generated tags
            metadata: Additional metadata about tag generation
        """
        try:
            if not self.firestore_manager or not self.firestore_manager.db:
                return

            cache_data = {
                "tags": tags,
                "cached_at": datetime.utcnow().isoformat(),
                "metadata": metadata,
                "content_hash": content_hash,
            }

            doc_ref = self.firestore_manager.db.collection(
                self.cache_collection
            ).document(content_hash)
            await doc_ref.set(cache_data)

            logger.debug(f"Cached tags for content hash: {content_hash}")

        except Exception as e:
            logger.error(f"Failed to cache tags: {e}")

    async def generate_tags(
        self,
        content: str,
        existing_metadata: dict[str, Any] | None = None,
        max_tags: int = 5,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        Generate intelligent tags for document content using OpenAI API.

        Args:
            content: Document content to analyze
            existing_metadata: Existing document metadata for context
            max_tags: Maximum number of tags to generate
            use_cache: Whether to use cached results

        Returns:
            Dictionary with generated tags and metadata
        """
        await self._ensure_initialized()

        if not OPENAI_AVAILABLE or not openai_client:
            return {
                "status": "failed",
                "error": "OpenAI client not available for tag generation",
                "tags": [],
            }

        try:
            content_hash = self._generate_content_hash(content)

            # Check cache first if enabled
            if use_cache:
                cached_result = await self._get_cached_tags(content_hash)
                if cached_result:
                    return {
                        "status": "success",
                        "tags": cached_result.get("tags", []),
                        "source": "cache",
                        "cached_at": cached_result.get("cached_at"),
                        "content_hash": content_hash,
                    }

            # Prepare context from existing metadata
            context_info = ""
            if existing_metadata:
                context_parts = []
                if existing_metadata.get("author"):
                    context_parts.append(f"Author: {existing_metadata['author']}")
                if existing_metadata.get("category"):
                    context_parts.append(f"Category: {existing_metadata['category']}")
                if existing_metadata.get("source"):
                    context_parts.append(f"Source: {existing_metadata['source']}")
                if existing_metadata.get("year"):
                    context_parts.append(f"Year: {existing_metadata['year']}")

                if context_parts:
                    context_info = f"\n\nExisting metadata: {', '.join(context_parts)}"

            # Prepare prompt for OpenAI
            prompt = f"""Analyze the following document content and generate {max_tags} relevant, specific tags that best describe the content, topics, and themes.

Tags should be:
- Specific and descriptive (not generic)
- Relevant to the main topics and themes
- Useful for categorization and search
- Single words or short phrases (2-3 words max)
- Lowercase

Document content:
{content[:2000]}...{context_info}

Generate exactly {max_tags} tags as a comma-separated list:"""

            # Call OpenAI API
            response = await openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert document analyzer that generates precise, relevant tags for content categorization and search.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.3,
            )

            # Parse response
            tags_text = response.choices[0].message.content.strip()
            tags = [tag.strip().lower() for tag in tags_text.split(",") if tag.strip()]

            # Limit to max_tags
            tags = tags[:max_tags]

            # Prepare result metadata
            result_metadata = {
                "model": "gpt-3.5-turbo",
                "generated_at": datetime.utcnow().isoformat(),
                "content_length": len(content),
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            # Cache the result
            if use_cache:
                await self._cache_tags(content_hash, tags, result_metadata)

            return {
                "status": "success",
                "tags": tags,
                "source": "openai",
                "content_hash": content_hash,
                "metadata": result_metadata,
            }

        except Exception as e:
            logger.error(f"Failed to generate tags: {e}")
            return {"status": "failed", "error": str(e), "tags": []}

    async def enhance_metadata_with_tags(
        self,
        doc_id: str,
        content: str,
        existing_metadata: dict[str, Any],
        max_tags: int = 5,
    ) -> dict[str, Any]:
        """
        Enhance existing metadata with auto-generated tags.

        Args:
            doc_id: Document identifier
            content: Document content
            existing_metadata: Current metadata
            max_tags: Maximum number of tags to generate

        Returns:
            Enhanced metadata with auto-generated tags
        """
        try:
            # Generate tags
            tag_result = await self.generate_tags(content, existing_metadata, max_tags)

            if tag_result["status"] != "success":
                logger.warning(
                    f"Failed to generate tags for doc_id {doc_id}: {tag_result.get('error')}"
                )
                return existing_metadata

            # Enhance metadata
            enhanced_metadata = existing_metadata.copy()

            # Add auto-generated tags
            auto_tags = tag_result["tags"]
            enhanced_metadata["auto_tags"] = auto_tags
            enhanced_metadata["auto_tag_metadata"] = {
                "generated_at": tag_result.get("metadata", {}).get("generated_at"),
                "source": tag_result.get("source"),
                "content_hash": tag_result.get("content_hash"),
                "tag_count": len(auto_tags),
            }

            # Merge with existing tags if present
            existing_tags = existing_metadata.get("tags", [])
            if isinstance(existing_tags, str):
                existing_tags = [existing_tags]
            elif not isinstance(existing_tags, list):
                existing_tags = []

            # Combine tags (remove duplicates)
            all_tags = list(set(existing_tags + auto_tags))
            enhanced_metadata["tags"] = all_tags

            # Update hierarchy levels based on tags
            if not enhanced_metadata.get("level_2") and auto_tags:
                enhanced_metadata["level_2"] = auto_tags[
                    0
                ]  # Use first auto-tag as level_2

            logger.info(
                f"Enhanced metadata for doc_id {doc_id} with {len(auto_tags)} auto-generated tags"
            )

            return enhanced_metadata

        except Exception as e:
            logger.error(
                f"Failed to enhance metadata with tags for doc_id {doc_id}: {e}"
            )
            return existing_metadata

    async def batch_generate_tags(
        self, documents: list[dict[str, Any]], max_tags: int = 5
    ) -> dict[str, Any]:
        """
        Generate tags for multiple documents in batch.

        Args:
            documents: List of document dictionaries with 'doc_id', 'content', and optional 'metadata'
            max_tags: Maximum number of tags per document

        Returns:
            Batch operation results
        """
        await self._ensure_initialized()

        results = []
        successful = 0
        failed = 0

        for doc in documents:
            doc_id = doc.get("doc_id")
            content = doc.get("content")
            metadata = doc.get("metadata", {})

            if not doc_id or not content:
                result = {
                    "doc_id": doc_id or "unknown",
                    "status": "failed",
                    "error": "Missing doc_id or content",
                    "tags": [],
                }
                results.append(result)
                failed += 1
                continue

            try:
                tag_result = await self.generate_tags(content, metadata, max_tags)
                result = {
                    "doc_id": doc_id,
                    "status": tag_result["status"],
                    "tags": tag_result["tags"],
                    "source": tag_result.get("source"),
                    "content_hash": tag_result.get("content_hash"),
                }

                if tag_result["status"] == "success":
                    successful += 1
                else:
                    failed += 1
                    result["error"] = tag_result.get("error")

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to generate tags for doc_id {doc_id}: {e}")
                result = {
                    "doc_id": doc_id,
                    "status": "failed",
                    "error": str(e),
                    "tags": [],
                }
                results.append(result)
                failed += 1

        return {
            "status": "completed",
            "total_documents": len(documents),
            "successful": successful,
            "failed": failed,
            "results": results,
        }

    async def clear_cache(self, older_than_hours: int | None = None) -> dict[str, Any]:
        """
        Clear cached tags from Firestore.

        Args:
            older_than_hours: Only clear cache older than specified hours (None for all)

        Returns:
            Operation result
        """
        try:
            if not self.firestore_manager or not self.firestore_manager.db:
                return {"status": "failed", "error": "Firestore not initialized"}

            collection_ref = self.firestore_manager.db.collection(self.cache_collection)

            if older_than_hours is None:
                # Delete all cache entries
                docs = collection_ref.stream()
                deleted_count = 0

                async for doc in docs:
                    await doc.reference.delete()
                    deleted_count += 1

                return {
                    "status": "success",
                    "deleted_count": deleted_count,
                    "message": "All cache entries deleted",
                }
            else:
                # Delete only old cache entries
                cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
                docs = collection_ref.where(
                    "cached_at", "<", cutoff_time.isoformat()
                ).stream()
                deleted_count = 0

                async for doc in docs:
                    await doc.reference.delete()
                    deleted_count += 1

                return {
                    "status": "success",
                    "deleted_count": deleted_count,
                    "message": f"Deleted cache entries older than {older_than_hours} hours",
                }

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return {"status": "failed", "error": str(e)}


# Global instance
_auto_tagging_tool = None


def get_auto_tagging_tool() -> AutoTaggingTool:
    """Get the global AutoTaggingTool instance."""
    global _auto_tagging_tool
    if _auto_tagging_tool is None:
        _auto_tagging_tool = AutoTaggingTool()
    return _auto_tagging_tool


# Convenience functions for external use
async def auto_generate_tags(
    content: str,
    existing_metadata: dict[str, Any] | None = None,
    max_tags: int = 5,
    use_cache: bool = True,
) -> dict[str, Any]:
    """
    Generate intelligent tags for document content.

    Args:
        content: Document content to analyze
        existing_metadata: Existing document metadata for context
        max_tags: Maximum number of tags to generate
        use_cache: Whether to use cached results

    Returns:
        Dictionary with generated tags and metadata
    """
    tool = get_auto_tagging_tool()
    return await tool.generate_tags(content, existing_metadata, max_tags, use_cache)


async def enhance_document_metadata(
    doc_id: str, content: str, existing_metadata: dict[str, Any], max_tags: int = 5
) -> dict[str, Any]:
    """
    Enhance document metadata with auto-generated tags.

    Args:
        doc_id: Document identifier
        content: Document content
        existing_metadata: Current metadata
        max_tags: Maximum number of tags to generate

    Returns:
        Enhanced metadata with auto-generated tags
    """
    tool = get_auto_tagging_tool()
    return await tool.enhance_metadata_with_tags(
        doc_id, content, existing_metadata, max_tags
    )
