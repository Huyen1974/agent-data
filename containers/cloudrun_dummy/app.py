from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def hello():
    """Minimal dummy Cloud Run endpoint for CI testing"""
    return jsonify({"message": "Dummy Cloud Run working", "status": "success"})

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port) 