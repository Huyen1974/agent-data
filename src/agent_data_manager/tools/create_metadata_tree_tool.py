def create_metadata_tree(documents):
    """Tạo một cây metadata đơn giản từ danh sách documents."""
    tree = {doc["id"]: doc.get("metadata", {}) for doc in documents}
    return {"tree": tree}
