def semantic_search_by_year(tree, year_keyword):
    """Tìm kiếm theo năm (year) khớp semantic."""
    matches = {
        doc_id: meta
        for doc_id, meta in tree.items()
        if year_keyword.lower() in str(meta.get("year", "")).lower()
    }
    return {"year_matches": matches}
