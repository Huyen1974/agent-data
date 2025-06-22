def conditional_search_metadata(tree, conditions):
    """Tìm kiếm node có metadata khớp với TẤT CẢ điều kiện.

    Args:
        tree (dict): Cây metadata.
        conditions (dict): Dict các điều kiện key-value (logic AND).
    """
    matches = {}
    for doc_id, meta in tree.items():
        match_all = True
        for key, value in conditions.items():
            if meta.get(key) != value:
                match_all = False
                break
        if match_all:
            matches[doc_id] = meta
    return {"conditional_matches": matches}
