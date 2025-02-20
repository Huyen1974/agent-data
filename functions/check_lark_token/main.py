import requests
import json
import os
from google.cloud import secretmanager
from flask import jsonify

# Cấu hình (THAY ĐỔI CÁC GIÁ TRỊ NÀY CHO PHÙ HỢP)
PROJECT_ID = os.environ.get("PROJECT_ID")  # Hoặc "github-chatgpt-ggcloud"
LARK_USER_INFO_URL = "https://open.larksuite.com/open-apis/authen/v1/access_token"  # Thay bằng URL THẬT để lấy thông tin user (hoặc API khác)
LARK_GENERATE_TOKEN_URL = "https://asia-southeast1-github-chatgpt-ggcloud.cloudfunctions.net/generate-lark-token"
SECRET_NAME = "lark-access-token-sg"
MAX_RETRIES = 6  # Tổng số lần thử (3 lần ban đầu + 3 lần sau khi gọi generate)

def get_lark_token():
    """Lấy token từ Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{SECRET_NAME}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def validate_lark_token(token):
    """Kiểm tra token bằng cách gọi API lấy thông tin user (GIẢ ĐỊNH)."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(LARK_USER_INFO_URL, headers=headers)
    return response.status_code == 200  # Giả định status code 200 là OK

def call_generate_lark_token():
    """Gọi Cloud Function generate-lark-token."""
    try:
        response = requests.get(LARK_GENERATE_TOKEN_URL)
        response.raise_for_status()
        return True  # Trả về True nếu gọi thành công
    except requests.exceptions.RequestException as e:
        print(f"Error calling generate-lark-token: {e}")
        return False

# Thay thế hàm send email của bạn
def send_error_email(log_message):
    """Gửi email thông báo lỗi (ví dụ)."""
    print("Đã có lỗi xảy ra")
    print(log_message)
    # Ví dụ: Bạn có thể sử dụng thư viện smtplib để gửi email
    # import smtplib
    # from email.mime.text import MIMEText

    # msg = MIMEText(log_message)
    # msg['Subject'] = "Lark Token Error"
    # msg['From'] = SENDER_EMAIL
    # msg['To'] = RECEIVER_EMAIL

    # try:
    #     with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server: #Sử dụng gmail và cổng 465
    #         server.login(SENDER_EMAIL, SENDER_PASSWORD) #Đăng nhập
    #         server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string()) #Gửi mail
    #     print("Email sent successfully!")
    # except Exception as e:
    #     print(f"Error sending email: {e}")

def check_lark_token(request):
    """Cloud Function để kiểm tra Lark token."""
    log = ""

    for attempt in range(MAX_RETRIES):  # Tổng cộng 6 lần thử (3 lần ban đầu + 3 lần sau khi gọi generate)
        token = get_lark_token()
        if validate_lark_token(token):
            return jsonify({"status": "OK", "message": "Token is valid"})

        log += f"Attempt {attempt + 1}: Token invalid. Calling generate-lark-token...\n"
        if not call_generate_lark_token(): # Gọi function
            log += "  Failed to call generate-lark-token.\n"
            #return "ERROR: Could not generate new token." # Không return sớm
            # Không return mà vẫn tiếp tục cho phép retry
        
        if attempt < MAX_RETRIES-1: #Nếu vẫn chưa phải là lần cuối
            time.sleep(3)  # Đợi 3 giây


    # Nếu vẫn không hợp lệ sau 6 lần thử
    log += "ERROR: Token still invalid after multiple attempts and regeneration.\n"
    send_error_email(log) #Gửi email bằng hàm bạn đã tạo
    return jsonify({"status": "ERROR", "message": f"Token invalid after {MAX_RETRIES} attempts."}), 401
