def multi_update_metadata(tree, updates):
    """Cập nhật metadata đồng loạt cho nhiều document.

    Args:
        tree (dict): Cây metadata hiện tại.
        updates (list): Danh sách các bản cập nhật, mỗi phần tử là dict dạng
                        {'doc_id': 'id', 'new_metadata': {'key': 'value'}}
    """
    for update in updates:
        doc_id = update.get("doc_id")
        new_metadata = update.get("new_metadata")
        if doc_id and new_metadata and doc_id in tree:
            tree[doc_id].update(new_metadata)
    return {"updated_tree": tree}
