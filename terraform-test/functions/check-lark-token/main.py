from flask import Flask, request
from google.cloud import firestore
from google.cloud import secretmanager
from google.cloud import storage
import requests
from datetime import datetime, timezone, timedelta
import time

app = Flask(__name__)
firestore_client = firestore.Client(project="github-chatgpt-ggcloud")
secret_client = secretmanager.SecretManagerServiceClient()
storage_client = storage.Client(project="github-chatgpt-ggcloud")

def get_lark_token():
    secret_name = "projects/github-chatgpt-ggcloud/secrets/lark-access-token-sg/versions/latest"
    response = secret_client.access_secret_version(request={"name": secret_name})
    return response.payload.data.decode("UTF-8")

def refresh_lark_token():
    generate_url = "https://asia-southeast1-github-chatgpt-ggcloud.cloudfunctions.net/generate-lark-token"
    try:
        response = requests.get(generate_url)
        return response.status_code == 200
    except Exception as e:
        return False

def log_error(error_message):
    bucket_name = "huyen1974-log-storage"
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    file_path = f"check_lark_token/{date_str}/errors.log"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    try:
        existing_content = blob.download_as_text() if blob.exists() else ""
        new_content = f"{existing_content}\n{datetime.now(timezone.utc).isoformat()} - {error_message}"
        blob.upload_from_string(new_content)
    except Exception as e:
        print(f"Failed to log error: {str(e)}")

@app.route("/check_lark_token", methods=["GET"])
def check_lark_token():
    try:
        doc_ref = firestore_client.collection("lark_tokens").document("latest_token")
        doc = doc_ref.get()
        if not doc.exists:
            log_error("Firestore document 'lark_tokens/latest_token' not found")
            return "mail failure to refresh Lark access token", 500

        token_data = doc.to_dict()
        token_timestamp = token_data.get("timestamp")
        if not token_timestamp:
            log_error("Timestamp not found in Firestore document")
            return "mail failure to refresh Lark access token", 500

        now = datetime.now(timezone.utc)
        time_diff = (now - token_timestamp).total_seconds() / 60

        if time_diff < 115:
            return {"status": "OK"}, 200

        retries = 0
        max_retries = 6
        while retries < max_retries:
            if refresh_lark_token():
                time.sleep(3)
                doc = doc_ref.get()
                token_data = doc.to_dict()
                new_timestamp = token_data.get("timestamp")
                if (datetime.now(timezone.utc) - new_timestamp).total_seconds() / 60 < 115:
                    return {"status": "OK"}, 200
            retries += 1
            time.sleep(3)

        error_message = f"Failed to refresh Lark token after {max_retries} retries"
        log_error(error_message)
        return "mail failure to refresh Lark access token", 500

    except Exception as e:
        log_error(f"Unexpected error: {str(e)}")
        return "mail failure to refresh Lark access token", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)