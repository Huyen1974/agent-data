def find_metadata_by_key(tree, key, value):
    """Tìm node có metadata key-value khớp."""
    matches = {doc_id: meta for doc_id, meta in tree.items() if meta.get(key) == value}
    return {"matches": matches}
