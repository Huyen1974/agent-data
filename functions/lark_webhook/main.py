import json
import functions_framework
from flask import request, jsonify

@functions_framework.http
def lark_webhook(request):
    """Hàm xử lý Webhook từ Lark Messenger"""
    try:
        # Nhận payload JSON từ Lark
        data = request.get_json()

        # Xác nhận challenge khi đăng ký Webhook
        if "challenge" in data:
            return jsonify({"challenge": data["challenge"]})

        # Kiểm tra xem đây có phải là sự kiện tin nhắn không
        if "event" in data and "message" in data["event"]:
            message = data["event"]["message"]
            sender = data["event"]["sender"]["sender_id"]["user_id"]
            message_text = message["content"]

            print(f"📩 Nhận tin nhắn từ {sender}: {message_text}")

            # TODO: Gửi message_text đến ChatGPT API để xử lý

            return jsonify({"status": "OK", "message": "Đã nhận tin nhắn từ Lark"}), 200
        
        return jsonify({"status": "ERROR", "message": "Sự kiện không hợp lệ"}), 400

    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 500
