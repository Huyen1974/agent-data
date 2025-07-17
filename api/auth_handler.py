"""
Cloud Function: Auth Handler
Handles authentication, user registration, and JWT token management
"""

import logging
import time

import functions_framework
from flask import Request, jsonify
from google.cloud import monitoring_v3

# Import Agent Data components
from ADK.agent_data.auth.auth_manager import AuthManager
from ADK.agent_data.auth.user_manager import UserManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
auth_manager = None
user_manager = None
monitoring_client = None


def _initialize_components():
    """Initialize authentication components."""
    global auth_manager, user_manager, monitoring_client

    try:
        auth_manager = AuthManager()
        user_manager = UserManager()
        monitoring_client = monitoring_v3.MetricServiceClient()

        logger.info("Auth components initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize auth components: {e}")
        raise


def _record_auth_metric(operation: str, success: bool, latency_ms: float):
    """Record authentication metrics to Cloud Monitoring."""
    try:
        if not monitoring_client:
            return

        import os

        project_name = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}"

        # Record latency metric
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/auth/{operation}_latency"
        series.resource.type = "cloud_function"
        series.resource.labels["function_name"] = "auth-handler"

        point = monitoring_v3.Point()
        point.value.double_value = latency_ms
        point.interval.end_time.seconds = int(time.time())
        series.points = [point]

        # Record success/failure metric
        success_series = monitoring_v3.TimeSeries()
        success_series.metric.type = f"custom.googleapis.com/auth/{operation}_success"
        success_series.resource.type = "cloud_function"
        success_series.resource.labels["function_name"] = "auth-handler"

        success_point = monitoring_v3.Point()
        success_point.value.int64_value = 1 if success else 0
        success_point.interval.end_time.seconds = int(time.time())
        success_series.points = [success_point]

        monitoring_client.create_time_series(
            name=project_name, time_series=[series, success_series]
        )

    except Exception as e:
        logger.warning(f"Failed to record auth metric: {e}")


@functions_framework.http
def auth_handler(request: Request):
    """
    Authentication Cloud Function handler.
    Handles login, registration, token validation, and user management.
    """
    start_time = time.time()

    # Initialize components on first request
    if auth_manager is None:
        _initialize_components()

    try:
        # Parse request
        path = request.path.strip("/")
        method = request.method

        logger.info(f"Processing auth {method} /{path}")

        # Route to appropriate auth handler
        if path == "login" and method == "POST":
            result, success = _handle_login(request)
            operation = "login"
        elif path == "register" and method == "POST":
            result, success = _handle_register(request)
            operation = "register"
        elif path == "validate" and method == "POST":
            result, success = _handle_validate_token(request)
            operation = "validate"
        elif path == "refresh" and method == "POST":
            result, success = _handle_refresh_token(request)
            operation = "refresh"
        elif path == "logout" and method == "POST":
            result, success = _handle_logout(request)
            operation = "logout"
        else:
            return jsonify({"error": "Auth endpoint not found"}), 404

        # Record metrics
        latency_ms = (time.time() - start_time) * 1000
        _record_auth_metric(operation, success, latency_ms)

        return result

    except Exception as e:
        logger.error(f"Auth handler error: {e}")
        return jsonify({"error": "Authentication service error"}), 500


def _handle_login(request: Request) -> tuple:
    """Handle user login with email/password."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400, False

        # Support both form data and JSON
        username = data.get("username") or data.get("email")
        password = data.get("password")

        if not username or not password:
            return (
                jsonify({"error": "Username/email and password are required"}),
                400,
                False,
            )

        # Validate credentials
        user_info = user_manager.authenticate_user(username, password)
        if not user_info:
            return jsonify({"error": "Invalid credentials"}), 401, False

        # Generate JWT token
        token_data = auth_manager.create_access_token(
            user_id=user_info["user_id"],
            email=user_info["email"],
            scopes=user_info.get("scopes", ["read", "write"]),
        )

        response_data = {
            "access_token": token_data["access_token"],
            "token_type": "bearer",
            "expires_in": token_data["expires_in"],
            "user_id": user_info["user_id"],
            "email": user_info["email"],
            "scopes": user_info.get("scopes", ["read", "write"]),
        }

        logger.info(f"User logged in successfully: {user_info['email']}")
        return jsonify(response_data), 200, True

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Login failed"}), 500, False


def _handle_register(request: Request) -> tuple:
    """Handle user registration."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400, False

        email = data.get("email")
        password = data.get("password")
        full_name = data.get("full_name")

        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400, False

        if len(password) < 6:
            return (
                jsonify({"error": "Password must be at least 6 characters"}),
                400,
                False,
            )

        # Check if user already exists
        existing_user = user_manager.get_user_by_email(email)
        if existing_user:
            return jsonify({"error": "User already exists"}), 409, False

        # Create new user
        user_result = user_manager.create_user(
            email=email, password=password, full_name=full_name
        )

        if not user_result.get("success"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Registration failed",
                        "error": user_result.get("error", "Unknown error"),
                    }
                ),
                500,
                False,
            )

        response_data = {
            "status": "success",
            "message": "User registered successfully",
            "user_id": user_result["user_id"],
            "email": email,
        }

        logger.info(f"User registered successfully: {email}")
        return jsonify(response_data), 201, True

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return (
            jsonify(
                {"status": "error", "message": "Registration failed", "error": str(e)}
            ),
            500,
            False,
        )


def _handle_validate_token(request: Request) -> tuple:
    """Handle JWT token validation."""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify({"error": "Missing or invalid Authorization header"}),
                401,
                False,
            )

        token = auth_header.split(" ")[1]

        # Validate token
        user_info = auth_manager.verify_token(token)
        if not user_info:
            return jsonify({"error": "Invalid or expired token"}), 401, False

        response_data = {
            "valid": True,
            "user_id": user_info["user_id"],
            "email": user_info["email"],
            "scopes": user_info.get("scopes", []),
            "expires_at": user_info.get("exp"),
        }

        return jsonify(response_data), 200, True

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({"error": "Token validation failed"}), 500, False


def _handle_refresh_token(request: Request) -> tuple:
    """Handle JWT token refresh."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400, False

        refresh_token = data.get("refresh_token")
        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400, False

        # Validate and refresh token
        new_token_data = auth_manager.refresh_access_token(refresh_token)
        if not new_token_data:
            return jsonify({"error": "Invalid or expired refresh token"}), 401, False

        response_data = {
            "access_token": new_token_data["access_token"],
            "token_type": "bearer",
            "expires_in": new_token_data["expires_in"],
            "refresh_token": new_token_data.get("refresh_token", refresh_token),
        }

        return jsonify(response_data), 200, True

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({"error": "Token refresh failed"}), 500, False


def _handle_logout(request: Request) -> tuple:
    """Handle user logout (token invalidation)."""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify({"error": "Missing or invalid Authorization header"}),
                401,
                False,
            )

        token = auth_header.split(" ")[1]

        # Invalidate token (add to blacklist)
        success = auth_manager.invalidate_token(token)
        if not success:
            return jsonify({"error": "Failed to logout"}), 500, False

        response_data = {"status": "success", "message": "Logged out successfully"}

        return jsonify(response_data), 200, True

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500, False
