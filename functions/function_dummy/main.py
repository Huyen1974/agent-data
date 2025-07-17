import functions_framework
from flask import jsonify


@functions_framework.http
def hello_function(request):
    """Minimal dummy Cloud Function for CI testing"""
    return jsonify({"message": "Hello from Cloud Function", "status": "success"})
