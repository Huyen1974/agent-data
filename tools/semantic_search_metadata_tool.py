def semantic_search_metadata(tree, keyword):
    """Giả lập tìm kiếm semantic đơn giản."""
    matches = {
        doc_id: meta
        for doc_id, meta in tree.items()
        if keyword.lower() in str(meta).lower()
    }
    return {"semantic_matches": matches}
