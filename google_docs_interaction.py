from google.oauth2 import service_account
from googleapiclient.discovery import build

# Đường dẫn đến tệp JSON credentials đã được tải xuống từ Google Cloud Console
SERVICE_ACCOUNT_FILE = '/Users/nmhuyen/Documents/chatgpt-githubnew/github-chatgpt-ggcloud-cbb20cb8c7ed.json'
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

# ID của Google Docs cần được chia sẻ và ghi dữ liệu vào
DOCUMENT_ID = '1Lwhd7ZmVo19BmPdb73XgKj7EZmCimDS4wBnLwFdcCFY'

# Thiết lập thông tin xác thực
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Kết nối với Google Drive API để chia sẻ tài liệu
drive_service = build('drive', 'v3', credentials=credentials)

# Lấy địa chỉ email của tài khoản dịch vụ từ file credentials
service_account_email = credentials.service_account_email

# Thực hiện chia sẻ tài liệu với quyền Editor cho tài khoản dịch vụ
permission = {
    'type': 'user',
    'role': 'writer',
    'emailAddress': service_account_email
}

# Tạo quyền truy cập cho tài liệu
drive_service.permissions().create(
    fileId=DOCUMENT_ID,
    body=permission,
    fields='id'
).execute()

print("Đã cấp quyền Editor cho tài khoản dịch vụ thành công!")

# Kết nối tới Google Docs API để thêm nội dung vào tài liệu
docs_service = build('docs', 'v1', credentials=credentials)

# Nội dung cần thêm vào tài liệu
text_to_add = "ĐÃ TỰ GHI, SỬA, XOÁ, ĐỌC"

# Thực hiện yêu cầu ghi vào tài liệu
requests = [
    {
        'insertText': {
            'location': {
                'index': 1  # Thêm nội dung vào đầu tài liệu
            },
            'text': text_to_add
        }
    }
]

result = docs_service.documents().batchUpdate(
    documentId=DOCUMENT_ID, body={'requests': requests}
).execute()

print("Đã thêm nội dung thành công!")

