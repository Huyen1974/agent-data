import os
from datetime import datetime


def save_document(doc_id, content, save_dir="saved_documents"):
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{doc_id}.txt"
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Document '{doc_id}' saved successfully at {datetime.now()}"
