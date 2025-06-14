# FAISS Tools Archive

This directory contains FAISS-related tools that have been archived as part of CLI140m.

## Archived Tools

The following tools have been moved to this archive directory:

- `save_metadata_to_faiss_tool.py` - Tool for saving metadata to FAISS indices
- `load_metadata_from_faiss_tool.py` - Tool for loading metadata from FAISS indices  
- `query_metadata_faiss_tool.py` - Tool for querying FAISS indices
- `advanced_query_faiss_tool.py` - Advanced FAISS query functionality
- `rebuild_metadata_tree_from_faiss_tool.py` - Tool for rebuilding metadata trees from FAISS

## Reason for Archiving

These tools were archived during CLI140m coverage enhancement because:

1. **Zero Coverage**: These tools had 0% test coverage
2. **Migration to Qdrant**: The system has migrated from FAISS to Qdrant for vector storage
3. **Maintenance Burden**: FAISS tools were not actively maintained or used
4. **Coverage Goals**: Archiving these tools helps focus coverage efforts on active modules

## Git History Preservation

All tools were moved using `git mv` to preserve their complete git history. You can still access the full development history of these tools.

## Recovery

If any of these tools need to be restored in the future:

1. Use `git mv` to move them back to the `tools/` directory
2. Update imports and dependencies as needed
3. Add appropriate test coverage
4. Update the tool registry to include them

## CLI140m Context

This archiving was performed as part of CLI140m objectives:
- Increase coverage for main modules (api_mcp_gateway.py, qdrant_vectorization_tool.py, document_ingestion_tool.py) to ≥80%
- Increase overall coverage to >20%
- Archive unused FAISS tools to focus testing efforts

Date: 2025-01-14
CLI: CLI140m 