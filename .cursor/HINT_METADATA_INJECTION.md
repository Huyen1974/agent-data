# Metadata Injection System Design

## Overview
This document outlines the design for a comprehensive metadata injection system that standardizes metadata fields across all document ingestion operations in the Agent Data system.

## Standardized Metadata Schema

### Core Fields (Always Present)
- `doc_id`: String - Unique document identifier
- `source_path`: String - Original file path or source location
- `doc_type`: String - Document type (text, pdf, code, etc.)
- `created_at`: ISO timestamp - Document creation/ingestion time
- `updated_at`: ISO timestamp - Last update time
- `tags`: List[String] - Document tags for categorization
- `content_length`: Integer - Length of document content
- `content_hash`: String - MD5 hash of content for change detection

### Optional Fields (Context Dependent)
- `author`: String - Document author if available
- `language`: String - Document language (auto-detected or specified)
- `category`: String - Document category
- `format`: String - Original format (txt, pdf, docx, etc.)
- `encoding`: String - Text encoding
- `file_size`: Integer - Original file size in bytes
- `mime_type`: String - MIME type of original file

### System Fields (Internal Use)
- `ingestion_version`: String - Version of ingestion system
- `embedding_model`: String - Model used for vectorization
- `vector_dimension`: Integer - Dimension of generated vector
- `processing_pipeline`: String - Pipeline used for processing
- `ingestion_method`: String - Method of ingestion (api, batch, etc.)

### Hierarchical Fields (For Firestore)
- `level_1`: String - Primary category (doc_type)
- `level_2`: String - Secondary category (first tag)
- `level_3`: String - Tertiary category (author or source)
- `level_4`: String - Quaternary category (year or format)
- `level_5`: String - Quinary category (language)
- `level_6`: String - Senary category (additional classification)

## Implementation Strategy

### 1. MetadataInjector Class
- Centralized metadata injection logic
- Configurable field mapping
- Automatic detection of missing fields
- Validation of metadata schema

### 2. Integration Points
- Document ingestion pipeline
- Vectorization process
- Qdrant store operations
- Firestore metadata storage

### 3. Performance Considerations
- Lazy computation of optional fields
- Caching of frequently computed values
- Batch processing support
- Minimal overhead for existing operations

### 4. Testing Strategy
- Unit tests for metadata injection
- Integration tests with ingestion pipeline
- Performance tests for batch operations
- Validation tests for schema compliance

## Qdrant Index Strategy

### Indexed Fields for Fast Querying
- `tag`: KEYWORD index (existing)
- `doc_type`: KEYWORD index (new)
- `source_path`: KEYWORD index (new)
- `created_at`: DATETIME index (new)
- `language`: KEYWORD index (new)
- `category`: KEYWORD index (new)

### Filter Combinations
- By document type + tags
- By source path patterns
- By date ranges
- By language + category
- Complex multi-field filters

## Backward Compatibility
- Existing documents will be gradually migrated
- Old metadata fields will be preserved
- Migration utility for bulk updates
- Graceful handling of missing fields

## Usage Examples

### Basic Document Ingestion
```python
# Automatic metadata injection
result = await ingest_document(
    doc_id="example_doc",
    content="Sample content",
    source_path="/path/to/file.txt"
)
# Metadata automatically includes all standard fields
```

### Advanced Metadata Specification
```python
# With custom metadata
result = await ingest_document(
    doc_id="example_doc",
    content="Sample content",
    metadata={
        "source_path": "/path/to/file.txt",
        "author": "John Doe",
        "tags": ["research", "ai"],
        "category": "technical_paper"
    }
)
```

### Querying with Metadata
```python
# Search by document type
results = await qdrant_store.query_vectors_by_metadata(
    filter_conditions={"doc_type": "pdf", "language": "en"}
)

# Search by tags and date range
results = await qdrant_store.query_vectors_by_metadata(
    filter_conditions={
        "tags": ["research"],
        "created_at": {"gte": "2024-01-01"}
    }
)
```

## Migration Plan

### Phase 1: Core Implementation
- Implement MetadataInjector class
- Integrate with ingestion pipeline
- Add basic tests

### Phase 2: Enhanced Indexing
- Add Qdrant payload indices
- Implement advanced querying
- Performance optimization

### Phase 3: Migration Support
- Bulk migration utilities
- Backward compatibility features
- Documentation and examples

## Success Metrics
- All new documents have standardized metadata
- Query performance improved by 50%
- Test coverage > 90%
- Zero breaking changes to existing API 