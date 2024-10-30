from google.oauth2 import service_account
from googleapiclient.discovery import build
import googleapiclient.errors

# Đường dẫn đến file credentials JSON của bạn
CREDENTIALS_FILE = '/Users/nmhuyen/Documents/chatgpt-githubnew/github-chatgpt-ggcloud-cbb20cb8c7ed.json'

# Document ID của Google Docs mới
DOCUMENT_ID = '1nZgh_WAlFS3oydu3epsc46wgp5VmGoKX1wK6NprjFWM'

# Spreadsheet ID của Google Sheets (cập nhật với ID của file Google Sheets bạn tạo)
SPREADSHEET_ID = '1504zpGb6aZcdYJB7kjM-gydX-OXLEsLH2_yZ0G03Py0'

# Khởi tạo credentials từ file JSON
credentials = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=[
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
])

# Hàm kiểm tra quyền truy cập vào Google Drive
def check_drive_access():
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        drive_service.files().list(pageSize=1).execute()
        print("Quyền truy cập Google Drive: Thành công")
    except googleapiclient.errors.HttpError as error:
        print(f"Quyền truy cập Google Drive: Thất bại ({error})")

# Hàm kiểm tra quyền truy cập vào Google Docs
def check_docs_access():
    try:
        docs_service = build('docs', 'v1', credentials=credentials)
        docs_service.documents().get(documentId=DOCUMENT_ID).execute()
        print("Quyền truy cập Google Docs: Thành công")
    except googleapiclient.errors.HttpError as error:
        print(f"Quyền truy cập Google Docs: Thất bại ({error})")

# Hàm kiểm tra quyền truy cập vào Google Sheets
def check_sheets_access():
    try:
        sheets_service = build('sheets', 'v4', credentials=credentials)
        sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        print("Quyền truy cập Google Sheets: Thành công")
    except googleapiclient.errors.HttpError as error:
        print(f"Quyền truy cập Google Sheets: Thất bại ({error})")

# Chạy các hàm kiểm tra
check_drive_access()
check_docs_access()
check_sheets_access()

