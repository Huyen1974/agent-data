def semantic_search_multiple_fields(tree, search_terms):
    """Tìm kiếm semantic đồng thời trên nhiều trường.

    Args:
        tree (dict): Cây metadata.
        search_terms (dict): Dict dạng {'field_name': 'keyword'}.
                             Tìm các node mà keyword khớp semantic trong field_name tương ứng.
    """
    matches = {}
    for doc_id, meta in tree.items():
        match_all_fields = True
        for field, keyword in search_terms.items():
            field_value = meta.get(field)
            # Basic semantic check (keyword containment in string representation)
            if not (
                keyword and field_value and keyword.lower() in str(field_value).lower()
            ):
                match_all_fields = False
                break
        if match_all_fields:
            matches[doc_id] = meta
    return {"multi_field_semantic_matches": matches}
