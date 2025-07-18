# ⛔ CURSOR RULES – Agent Data Langroid (critical)

## 1. Project root (edit‑allowed ONLY)
/Users/nmhuyen/Documents/Manual Deploy/agent-data-langroid

✅ Mọi thao tác phải nằm trong thư mục này.  
⛔ Không được đọc/ghi/sửa ngoài path.

---

## 2. Dự án GitHub
Bạn đang làm việc với 2 repo:
- `agent-data-test`
- `agent-data-production`

Không được làm việc với các repo khác.

---

## 3. Artifact Registry
Mỗi repo trên sẽ có 1 Artifact Registry tương ứng:
- `agent-data-test`
- `agent-data-production`

☑️ Artifact Registry này lưu toàn bộ artifact cần dùng (Docker image, Cloud Function, Cloud Run...), không cần tách riêng từng loại.

---

## 4. CI/CD
Yêu cầu CI xanh cho:
- Cloud Function
- Cloud Run
- Workflow YAML

Sử dụng dummy để test CI/CD khi chưa có mã chính thức.

---

## 5. Terraform
- Các bucket sau đã có sẵn, Terraform cần tiếp quản quyền quản lý tương ứng theo repo:

| Bucket Name                                           | Thuộc repo |
|------------------------------------------------------|------------|
| huyen1974-agent-data-artifacts-test                  | test       |
| huyen1974-agent-data-artifacts-production            | production |
| huyen1974-agent-data-knowledge-test                  | test       |
| huyen1974-agent-data-knowledge-production            | production |
| huyen1974-agent-data-logs-test                       | test       |
| huyen1974-agent-data-logs-production                 | production |
| huyen1974-agent-data-qdrant-snapshots-test           | test       |
| huyen1974-agent-data-qdrant-snapshots-production     | production |
| huyen1974-agent-data-source-test                     | test       |
| huyen1974-agent-data-source-production               | production |
| huyen1974-agent-data-tfstate-test                    | test       |
| huyen1974-agent-data-tfstate-production              | production |

➡️ Những bucket trước đây do `agent-data` quản lý sẽ chuyển giao cho 2 repo mới tương ứng.

---

## 6. Secrets
- Secrets dùng chung lưu tại repo: `chatgpt-githubnew`
- Token/API key dùng chung lưu trong Secret Manager GCP (`github-chatgpt-ggcloud`)

---

## 7. Git
Mã luôn phải được đồng bộ:
- Trước khi làm: **pull bản mới nhất**
- Sau khi làm: **push bản cập nhật**

Không được làm việc trên mã cũ.

---

✅ Hãy tuân thủ nghiêm ngặt các quy tắc trên khi làm việc với dự án Agent Data Langroid. 