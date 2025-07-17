"""
Cloud Functions entry point for Agent Data API MCP Gateway
"""

import os
import sys

# Add the src directory to Python path for proper imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
sys.path.insert(0, src_path)

import json

import functions_framework

# Import the FastAPI app
try:
    from agent_data_manager.api_mcp_gateway import app

    FASTAPI_AVAILABLE = True
    print("FastAPI app imported successfully")
except ImportError as e:
    print(f"Warning: FastAPI app not available: {e}")
    FASTAPI_AVAILABLE = False
    app = None


@functions_framework.http
def main(request):
    """Cloud Functions entry point for Agent Data API MCP Gateway"""

    # Set CORS headers
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Content-Type": "application/json",
    }

    # Handle preflight requests
    if request.method == "OPTIONS":
        return ("", 204, headers)

    # If FastAPI app is available, use it for all requests
    if FASTAPI_AVAILABLE and app:
        try:
            # Convert Cloud Functions request to ASGI format
            from fastapi.testclient import TestClient

            client = TestClient(app)

            # Prepare request data
            method = request.method.lower()
            path = request.path if request.path else "/"

            # Handle query parameters
            query_params = dict(request.args) if hasattr(request, "args") else {}

            # Handle request body
            data = None
            json_data = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    json_data = request.get_json(silent=True)
                except:
                    pass

            # Handle headers
            request_headers = {}
            if hasattr(request, "headers"):
                for key, value in request.headers.items():
                    request_headers[key] = value

            # Make request to FastAPI app
            if method == "get":
                response = client.get(
                    path, params=query_params, headers=request_headers
                )
            elif method == "post":
                response = client.post(
                    path, json=json_data, params=query_params, headers=request_headers
                )
            elif method == "put":
                response = client.put(
                    path, json=json_data, params=query_params, headers=request_headers
                )
            elif method == "delete":
                response = client.delete(
                    path, params=query_params, headers=request_headers
                )
            else:
                response = client.get(
                    path, params=query_params, headers=request_headers
                )

            # Return FastAPI response
            response_headers = dict(headers)  # Start with CORS headers
            if hasattr(response, "headers"):
                for key, value in response.headers.items():
                    if key.lower() not in ["content-length", "transfer-encoding"]:
                        response_headers[key] = value

            return (response.content, response.status_code, response_headers)

        except Exception as e:
            print(f"Error using FastAPI app: {e}")
            # Fall back to mock responses
            pass

    # Fallback mock responses when FastAPI is not available
    # Handle health check
    if request.path in ["/health", "/", ""]:
        response_data = {
            "status": "healthy",
            "message": "Agent Data API MCP Gateway v2 (Fallback Mode)",
            "version": "2.0.0",
            "fastapi_available": FASTAPI_AVAILABLE,
        }
        return (json.dumps(response_data), 200, headers)

    # Handle cskh_query endpoint
    if request.path == "/cskh_query" and request.method == "POST":
        try:
            # Get request data
            request_json = request.get_json(silent=True)
            if not request_json:
                return (json.dumps({"error": "No JSON data provided"}), 400, headers)

            query = request_json.get("query", "")
            limit = request_json.get("limit", 8)

            # Mock response for fallback
            response_data = {
                "status": "success",
                "query": query,
                "limit": limit,
                "results": [
                    {
                        "id": "mock_fallback_1",
                        "content": f"Fallback mock response for query: {query}",
                        "score": 0.95,
                    }
                ],
                "message": "Fallback mock response from API MCP Gateway v2",
                "fastapi_available": FASTAPI_AVAILABLE,
            }

            return (json.dumps(response_data), 200, headers)

        except Exception as e:
            error_response = {
                "error": str(e),
                "status": "error",
                "fastapi_available": FASTAPI_AVAILABLE,
            }
            return (json.dumps(error_response), 500, headers)

    # Default response
    response_data = {
        "message": "Agent Data API MCP Gateway v2 (Fallback Mode)",
        "status": "running",
        "method": request.method,
        "path": request.path,
        "available_endpoints": ["/health", "/cskh_query"],
        "fastapi_available": FASTAPI_AVAILABLE,
    }

    return (json.dumps(response_data), 200, headers)


# For local testing
if __name__ == "__main__":
    import uvicorn

    if FASTAPI_AVAILABLE and app:
        # Run the FastAPI app directly
        port = int(os.environ.get("PORT", 8080))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        print("FastAPI app not available, cannot run locally")
