def semantic_search_by_author(tree, author_keyword):
    """Tìm kiếm theo tác giả (author) khớp semantic."""
    matches = {
        doc_id: meta
        for doc_id, meta in tree.items()
        if author_keyword.lower() in str(meta.get("author", "")).lower()
    }
    return {"author_matches": matches}
