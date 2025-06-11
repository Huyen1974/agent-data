def rebuild_metadata_tree(documents):
    """Xây dựng lại cây metadata từ danh sách documents mới.
    Hàm này tương tự create_metadata_tree nhưng dùng khi cần rebuild.
    """
    new_tree = {doc["id"]: doc.get("metadata", {}) for doc in documents}
    return {"rebuilt_tree": new_tree}
