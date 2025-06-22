def delete_metadata_node(tree, doc_id):
    """Xóa một nút khỏi cây metadata."""
    if doc_id in tree:
        del tree[doc_id]
    return {"updated_tree": tree}
