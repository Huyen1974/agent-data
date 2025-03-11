from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/", methods=["GET"])
def dummy_function():  # Không cần request ở đây
    return jsonify({"message": "Dummy function executed successfully!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
