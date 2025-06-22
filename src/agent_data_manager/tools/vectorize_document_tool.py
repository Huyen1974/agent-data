def vectorize_document(doc_id, content):
    """Giả lập chức năng vector hóa nội dung tài liệu."""
    # Trong thực tế sẽ gọi FAISS hoặc Embedding API
    return {"doc_id": doc_id, "vectorized": True, "content_length": len(content)}
