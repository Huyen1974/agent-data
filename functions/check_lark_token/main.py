import requests
import json
import os
import time  # ✅ Thêm dòng này để tránh lỗi

from google.cloud import secretmanager
from flask import jsonify


# Cấu hình
PROJECT_ID = os.environ.get("PROJECT_ID")  # Hoặc "github-chatgpt-ggcloud"
LARK_USER_INFO_URL = "https://open.larksuite.com/open-apis/authen/v1/access_token"
LARK_GENERATE_TOKEN_URL = "https://asia-southeast1-github-chatgpt-ggcloud.cloudfunctions.net/generate-lark-token"
SECRET_NAME = "lark-access-token-sg"
MAX_RETRIES = 6

def get_lark_token(request):  # Thêm tham số request
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def validate_lark_token(token):
    """Kiểm tra token bằng cách gọi API lấy thông tin user."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(LARK_USER_INFO_URL, headers=headers)
    return response.status_code == 200

def call_generate_lark_token():
    """Gọi Cloud Function generate-lark-token."""
    try:
        response = requests.get(LARK_GENERATE_TOKEN_URL)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error calling generate-lark-token: {e}")
        return False

def send_error_email(log_message):
    """Gửi email thông báo lỗi (ví dụ)."""
    print("Đã có lỗi xảy ra")
    print(log_message)

def check_lark_token(request):
    """Cloud Function để kiểm tra Lark token."""
    log = ""
    for attempt in range(MAX_RETRIES):
        token = get_lark_token(request)
        if validate_lark_token(token):
            return jsonify({"status": "OK", "message": "Token is valid"})
        log += f"Attempt {attempt + 1}: Token invalid. Calling generate-lark-token...\n"
        if not call_generate_lark_token():
            log += "  Failed to call generate-lark-token.\n"
        if attempt < MAX_RETRIES - 1:
            time.sleep(3)
    log += "ERROR: Token still invalid after multiple attempts and regeneration.\n"
    send_error_email(log)
    return jsonify({"status": "ERROR", "message": f"Token invalid after {MAX_RETRIES} attempts."}), 401
