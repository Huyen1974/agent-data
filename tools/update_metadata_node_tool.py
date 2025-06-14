def update_metadata_node(tree, doc_id, new_metadata):
    """Cập nhật metadata cho một node."""
    if doc_id in tree:
        tree[doc_id].update(new_metadata)
    return {"updated_tree": tree}
