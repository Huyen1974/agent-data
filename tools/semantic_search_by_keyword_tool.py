def semantic_search_by_keyword(tree, keyword):
    """Tìm kiếm từ khoá trong toàn bộ metadata."""
    matches = {doc_id: meta for doc_id, meta in tree.items() if keyword.lower() in str(meta).lower()}
    return {"keyword_matches": matches}
