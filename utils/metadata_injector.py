"""
Metadata Injection System for Agent Data
Standardizes metadata fields across all document ingestion operations.
"""

import hashlib
import mimetypes
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

# Version of the metadata injection system
METADATA_INJECTION_VERSION = "1.0.0"


class MetadataInjector:
    """
    Standardizes and injects metadata for document ingestion operations.
    
    This class ensures all documents have consistent metadata fields,
    making them easier to search, filter, and manage in the vector store.
    """
    
    def __init__(self, default_language: str = "en", default_embedding_model: str = "openai-ada-002"):
        """
        Initialize the MetadataInjector.
        
        Args:
            default_language: Default language for documents
            default_embedding_model: Default embedding model name
        """
        self.default_language = default_language
        self.default_embedding_model = default_embedding_model
        
        # Language detection patterns (simplified)
        self.language_patterns = {
            "en": [r"\b(the|and|or|but|in|on|at|to|for|of|with|by)\b"],
            "es": [r"\b(el|la|los|las|y|o|pero|en|con|por|para|de)\b"],
            "fr": [r"\b(le|la|les|et|ou|mais|dans|sur|pour|de|avec)\b"],
            "de": [r"\b(der|die|das|und|oder|aber|in|auf|für|von|mit)\b"],
            "it": [r"\b(il|la|i|le|e|o|ma|in|su|per|di|con)\b"],
            "pt": [r"\b(o|a|os|as|e|ou|mas|em|sobre|para|de|com)\b"],
            "ru": [r"\b(и|или|но|в|на|для|от|с|по|из)\b"],
            "zh": [r"[的|和|或|但|在|上|为|从|与|由]"],
            "ja": [r"[の|と|または|しかし|で|に|を|から|と|による]"],
            "ko": [r"[의|와|또는|하지만|에서|에|를|에서|와|에의해]"]
        }
        
        # Document type patterns
        self.doc_type_patterns = {
            "code": [r"\.(py|js|java|cpp|c|h|css|html|xml|json|yaml|yml|sql|sh|bash|zsh)$"],
            "pdf": [r"\.pdf$"],
            "text": [r"\.(txt|md|rst|asciidoc)$"],
            "office": [r"\.(doc|docx|xls|xlsx|ppt|pptx)$"],
            "image": [r"\.(jpg|jpeg|png|gif|bmp|svg|tiff|webp)$"],
            "audio": [r"\.(mp3|wav|flac|aac|ogg|wma)$"],
            "video": [r"\.(mp4|avi|mkv|mov|wmv|flv|webm)$"],
            "archive": [r"\.(zip|rar|7z|tar|gz|bz2|xz)$"],
            "config": [r"\.(conf|config|ini|cfg|toml|env|properties)$"],
            "log": [r"\.(log|logs)$"]
        }
        
        # Category mappings
        self.category_mappings = {
            "code": "development",
            "pdf": "document", 
            "text": "document",
            "office": "document",
            "image": "media",
            "audio": "media",
            "video": "media",
            "config": "configuration",
            "log": "system"
        }
    
    def inject_metadata(
        self,
        doc_id: str,
        content: str,
        source_path: Optional[str] = None,
        existing_metadata: Optional[Dict[str, Any]] = None,
        ingestion_method: str = "api",
        embedding_model: Optional[str] = None,
        vector_dimension: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Inject standardized metadata into a document.
        
        Args:
            doc_id: Unique document identifier
            content: Document content
            source_path: Original file path or source location
            existing_metadata: Existing metadata to preserve/merge
            ingestion_method: Method of ingestion (api, batch, etc.)
            embedding_model: Model used for vectorization
            vector_dimension: Dimension of generated vector
            tags: Additional tags for the document
            
        Returns:
            Enhanced metadata dictionary with all standardized fields
        """
        # Start with existing metadata or empty dict
        metadata = existing_metadata.copy() if existing_metadata else {}
        
        # Inject core fields
        metadata = self._inject_core_fields(
            metadata, doc_id, content, source_path, tags
        )
        
        # Inject optional fields
        metadata = self._inject_optional_fields(
            metadata, content, source_path
        )
        
        # Inject system fields
        metadata = self._inject_system_fields(
            metadata, ingestion_method, embedding_model, vector_dimension
        )
        
        # Inject hierarchical fields (for Firestore)
        metadata = self._inject_hierarchical_fields(metadata)
        
        # Validate metadata
        self._validate_metadata(metadata)
        
        return metadata
    
    def _inject_core_fields(
        self,
        metadata: Dict[str, Any],
        doc_id: str,
        content: str,
        source_path: Optional[str],
        tags: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Inject core metadata fields that are always present."""
        current_time = datetime.utcnow().isoformat()
        
        # Always set these core fields
        metadata["doc_id"] = doc_id
        metadata["content_length"] = len(content)
        metadata["content_hash"] = self._generate_content_hash(content)
        metadata["created_at"] = metadata.get("created_at", current_time)
        metadata["updated_at"] = current_time
        
        # Set source_path if provided
        if source_path:
            metadata["source_path"] = source_path
        elif "source_path" not in metadata:
            metadata["source_path"] = f"generated:{doc_id}"
        
        # Set doc_type based on source_path or content
        if "doc_type" not in metadata:
            metadata["doc_type"] = self._detect_doc_type(
                metadata["source_path"], content
            )
        
        # Set tags (merge with existing)
        existing_tags = metadata.get("tags", [])
        if tags:
            all_tags = list(set(existing_tags + tags))
        else:
            all_tags = existing_tags
        
        # Add auto-generated tags if none exist
        if not all_tags:
            all_tags = self._generate_auto_tags(metadata["doc_type"], content)
        
        metadata["tags"] = all_tags
        
        return metadata
    
    def _inject_optional_fields(
        self,
        metadata: Dict[str, Any],
        content: str,
        source_path: Optional[str]
    ) -> Dict[str, Any]:
        """Inject optional metadata fields based on available information."""
        
        # Detect language if not already set
        if "language" not in metadata:
            metadata["language"] = self._detect_language(content)
        
        # Set format and mime_type from source_path
        if source_path:
            if "format" not in metadata:
                metadata["format"] = self._extract_format(source_path)
            
            if "mime_type" not in metadata:
                metadata["mime_type"] = self._detect_mime_type(source_path)
            
            if "file_size" not in metadata and os.path.exists(source_path):
                try:
                    metadata["file_size"] = os.path.getsize(source_path)
                except (OSError, IOError):
                    pass
        
        # Set category if not already set
        if "category" not in metadata:
            metadata["category"] = self._determine_category(metadata)
        
        # Set encoding if not already set
        if "encoding" not in metadata:
            metadata["encoding"] = self._detect_encoding(content)
        
        # Extract author from content if not set (simple heuristic)
        if "author" not in metadata:
            detected_author = self._extract_author(content)
            if detected_author:
                metadata["author"] = detected_author
        
        return metadata
    
    def _inject_system_fields(
        self,
        metadata: Dict[str, Any],
        ingestion_method: str,
        embedding_model: Optional[str],
        vector_dimension: Optional[int]
    ) -> Dict[str, Any]:
        """Inject system-level metadata fields."""
        
        metadata["ingestion_version"] = METADATA_INJECTION_VERSION
        metadata["ingestion_method"] = ingestion_method
        metadata["processing_pipeline"] = "agent_data_ingestion"
        
        if embedding_model:
            metadata["embedding_model"] = embedding_model
        elif "embedding_model" not in metadata:
            metadata["embedding_model"] = self.default_embedding_model
        
        if vector_dimension:
            metadata["vector_dimension"] = vector_dimension
        
        return metadata
    
    def _inject_hierarchical_fields(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Inject hierarchical fields for Firestore organization."""
        
        # Level 1: Primary category (doc_type)
        if "level_1" not in metadata:
            metadata["level_1"] = metadata.get("doc_type", "document")
        
        # Level 2: Secondary category (first tag or category)
        if "level_2" not in metadata:
            tags = metadata.get("tags", [])
            if tags:
                metadata["level_2"] = tags[0]
            else:
                metadata["level_2"] = metadata.get("category", "general")
        
        # Level 3: Tertiary category (author or source domain)
        if "level_3" not in metadata:
            if "author" in metadata:
                metadata["level_3"] = metadata["author"]
            else:
                source_path = metadata.get("source_path", "")
                if source_path.startswith("http"):
                    # Extract domain from URL
                    parsed = urlparse(source_path)
                    metadata["level_3"] = parsed.netloc or "web"
                else:
                    # Extract directory from path
                    metadata["level_3"] = os.path.dirname(source_path) or "local"
        
        # Level 4: Quaternary category (year or format)
        if "level_4" not in metadata:
            created_at = metadata.get("created_at", "")
            if created_at:
                try:
                    year = datetime.fromisoformat(created_at.replace("Z", "+00:00")).year
                    metadata["level_4"] = str(year)
                except:
                    metadata["level_4"] = metadata.get("format", "unknown")
            else:
                metadata["level_4"] = metadata.get("format", "unknown")
        
        # Level 5: Quinary category (language)
        if "level_5" not in metadata:
            metadata["level_5"] = metadata.get("language", self.default_language)
        
        # Level 6: Senary category (additional classification)
        if "level_6" not in metadata:
            if "mime_type" in metadata:
                metadata["level_6"] = metadata["mime_type"].split("/")[0]
            else:
                metadata["level_6"] = "content"
        
        return metadata
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate MD5 hash of content for change detection."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:12]
    
    def _detect_doc_type(self, source_path: str, content: str) -> str:
        """Detect document type from source path and content."""
        source_path_lower = source_path.lower()
        
        # Check file extension patterns
        for doc_type, patterns in self.doc_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, source_path_lower):
                    return doc_type
        
        # Fallback to content analysis
        if self._looks_like_code(content):
            return "code"
        elif self._looks_like_markdown(content):
            return "text"
        else:
            return "text"
    
    def _detect_language(self, content: str) -> str:
        """Detect language from content using simple pattern matching."""
        content_lower = content.lower()
        
        # Score each language
        language_scores = {}
        for lang, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, content_lower)
                score += len(matches)
            language_scores[lang] = score
        
        # Return language with highest score, or default
        if language_scores:
            best_lang = max(language_scores, key=language_scores.get)
            if language_scores[best_lang] > 0:
                return best_lang
        
        return self.default_language
    
    def _extract_format(self, source_path: str) -> str:
        """Extract file format from source path."""
        _, ext = os.path.splitext(source_path)
        return ext.lstrip('.').lower() if ext else "unknown"
    
    def _detect_mime_type(self, source_path: str) -> str:
        """Detect MIME type from source path."""
        mime_type, _ = mimetypes.guess_type(source_path)
        return mime_type or "application/octet-stream"
    
    def _determine_category(self, metadata: Dict[str, Any]) -> str:
        """Determine document category from metadata."""
        doc_type = metadata.get("doc_type", "text")
        return self.category_mappings.get(doc_type, "general")
    
    def _detect_encoding(self, content: str) -> str:
        """Detect text encoding (simplified)."""
        # For now, assume UTF-8 since we're working with strings
        return "utf-8"
    
    def _extract_author(self, content: str) -> Optional[str]:
        """Extract author from content using simple heuristics."""
        # Look for common author patterns
        patterns = [
            r"(?:author|by|written by):\s*([^\n\r]+)",
            r"@author\s+([^\n\r]+)",
            r"# author:\s*([^\n\r]+)",
            r"author\s*=\s*[\"']([^\"']+)[\"']"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                if len(author) > 3 and len(author) < 100:
                    return author
        
        return None
    
    def _generate_auto_tags(self, doc_type: str, content: str) -> List[str]:
        """Generate automatic tags based on document type and content."""
        tags = [doc_type]
        
        # Add content-based tags
        content_lower = content.lower()
        
        # Technical terms
        if any(term in content_lower for term in ["api", "function", "class", "method"]):
            tags.append("technical")
        
        # Documentation terms
        if any(term in content_lower for term in ["readme", "documentation", "guide", "tutorial"]):
            tags.append("documentation")
        
        # Configuration terms
        if any(term in content_lower for term in ["config", "settings", "environment", "variable"]):
            tags.append("configuration")
        
        # Test terms
        if any(term in content_lower for term in ["test", "spec", "assert", "expect"]):
            tags.append("test")
        
        return tags
    
    def _looks_like_code(self, content: str) -> bool:
        """Check if content looks like code."""
        code_indicators = [
            "def ", "function ", "class ", "import ", "from ", "#!/",
            "<?php", "<!DOCTYPE", "<html>", "SELECT ", "INSERT ",
            "const ", "var ", "let ", "if(", "for(", "while("
        ]
        
        content_sample = content[:1000]  # Check first 1000 characters
        return any(indicator in content_sample for indicator in code_indicators)
    
    def _looks_like_markdown(self, content: str) -> bool:
        """Check if content looks like markdown."""
        markdown_indicators = [
            "# ", "## ", "### ", "- ", "* ", "1. ", "```", "**", "__", "[", "]("
        ]
        
        content_sample = content[:1000]  # Check first 1000 characters
        return any(indicator in content_sample for indicator in markdown_indicators)
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """Validate metadata structure and required fields."""
        required_fields = ["doc_id", "content_length", "content_hash", "created_at", "updated_at", "tags"]
        
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required metadata field: {field}")
        
        # Validate field types
        if not isinstance(metadata["doc_id"], str):
            raise ValueError("doc_id must be a string")
        
        if not isinstance(metadata["content_length"], int):
            raise ValueError("content_length must be an integer")
        
        if not isinstance(metadata["tags"], list):
            raise ValueError("tags must be a list")
        
        # Validate tag contents
        for tag in metadata["tags"]:
            if not isinstance(tag, str):
                raise ValueError("All tags must be strings")
    
    def batch_inject_metadata(
        self,
        documents: List[Dict[str, Any]],
        default_ingestion_method: str = "batch",
        default_embedding_model: Optional[str] = None,
        default_vector_dimension: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Inject metadata for a batch of documents.
        
        Args:
            documents: List of document dictionaries with at least doc_id and content
            default_ingestion_method: Default ingestion method for all documents
            default_embedding_model: Default embedding model for all documents
            default_vector_dimension: Default vector dimension for all documents
            
        Returns:
            List of document dictionaries with enhanced metadata
        """
        enhanced_documents = []
        
        for doc in documents:
            try:
                enhanced_metadata = self.inject_metadata(
                    doc_id=doc["doc_id"],
                    content=doc["content"],
                    source_path=doc.get("source_path"),
                    existing_metadata=doc.get("metadata", {}),
                    ingestion_method=doc.get("ingestion_method", default_ingestion_method),
                    embedding_model=doc.get("embedding_model", default_embedding_model),
                    vector_dimension=doc.get("vector_dimension", default_vector_dimension),
                    tags=doc.get("tags")
                )
                
                enhanced_doc = doc.copy()
                enhanced_doc["metadata"] = enhanced_metadata
                enhanced_documents.append(enhanced_doc)
                
            except Exception as e:
                logger.error(f"Failed to inject metadata for document {doc.get('doc_id', 'unknown')}: {e}")
                # Add the document with minimal metadata
                enhanced_doc = doc.copy()
                enhanced_doc["metadata"] = {
                    "doc_id": doc["doc_id"],
                    "content_length": len(doc["content"]),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "tags": ["error"],
                    "error": str(e)
                }
                enhanced_documents.append(enhanced_doc)
        
        return enhanced_documents


# Global instance for easy access
_metadata_injector = None


def get_metadata_injector(**kwargs) -> MetadataInjector:
    """Get or create the global MetadataInjector instance."""
    global _metadata_injector
    if _metadata_injector is None:
        _metadata_injector = MetadataInjector(**kwargs)
    return _metadata_injector


def inject_document_metadata(
    doc_id: str,
    content: str,
    source_path: Optional[str] = None,
    existing_metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to inject metadata for a single document.
    
    Args:
        doc_id: Document identifier
        content: Document content
        source_path: Source file path
        existing_metadata: Existing metadata to merge
        **kwargs: Additional arguments passed to inject_metadata
        
    Returns:
        Enhanced metadata dictionary
    """
    injector = get_metadata_injector()
    return injector.inject_metadata(
        doc_id=doc_id,
        content=content,
        source_path=source_path,
        existing_metadata=existing_metadata,
        **kwargs
    ) 