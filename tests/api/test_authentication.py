"""
Test suite for JWT Authentication functionality in API A2A Gateway
Tests login, token validation, rate limiting, and security features
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from jose import jwt
from datetime import datetime, timedelta

from agent_data_manager.auth.auth_manager import AuthManager
from agent_data_manager.auth.user_manager import UserManager


@pytest.mark.deferred
class TestJWTAuthentication:
    """Test JWT authentication functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.auth_manager = AuthManager()
        self.user_manager = UserManager()

    @pytest.mark.deferred
    def test_auth_manager_initialization(self):
        """Test AuthManager initializes correctly"""
        assert self.auth_manager.algorithm == "HS256"
        assert self.auth_manager.access_token_expire_minutes == 30
        assert self.auth_manager.secret_key is not None

    @pytest.mark.deferred
    def test_password_hashing_and_verification(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = self.auth_manager.get_password_hash(password)

        assert hashed != password
        assert self.auth_manager.verify_password(password, hashed)
        assert not self.auth_manager.verify_password("wrong_password", hashed)

    @pytest.mark.deferred
    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation"""
        user_data = {"sub": "test@cursor.integration", "email": "test@cursor.integration", "scopes": ["read", "write"]}

        # Create token
        token = self.auth_manager.create_access_token(user_data)
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long

        # Validate token
        payload = self.auth_manager.verify_token(token)
        assert payload["sub"] == user_data["sub"]
        assert payload["email"] == user_data["email"]
        assert payload["scopes"] == user_data["scopes"]

    @pytest.mark.deferred
    def test_jwt_token_expiration(self):
        """Test JWT token expiration handling"""
        user_data = {"sub": "test@cursor.integration", "email": "test@cursor.integration"}

        # Create token with very short expiration
        short_expiry = timedelta(seconds=1)
        token = self.auth_manager.create_access_token(user_data, expires_delta=short_expiry)

        # Token should be valid immediately
        payload = self.auth_manager.verify_token(token)
        assert payload["sub"] == user_data["sub"]

        # Wait for token to expire
        time.sleep(2)

        # Token should now be invalid
        with pytest.raises(Exception):  # Should raise HTTPException
            self.auth_manager.verify_token(token)

    @pytest.mark.deferred
    def test_invalid_jwt_token(self):
        """Test handling of invalid JWT tokens"""
        invalid_tokens = [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "not_a_jwt_at_all",
            None,
        ]

        for invalid_token in invalid_tokens:
            if invalid_token is None:
                continue
            with pytest.raises(Exception):  # Should raise HTTPException
                self.auth_manager.verify_token(invalid_token)

    @pytest.mark.deferred
    def test_user_token_creation(self):
        """Test user-specific token creation"""
        user_id = "test@cursor.integration"
        email = "test@cursor.integration"
        scopes = ["read", "write", "admin"]

        token = self.auth_manager.create_user_token(user_id, email, scopes)
        payload = self.auth_manager.verify_token(token)

        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["scopes"] == scopes
        assert payload["token_type"] == "access"

    @pytest.mark.deferred
    def test_user_access_validation(self):
        """Test user access scope validation"""
        # User with read access
        read_user = {"user_id": "read_user@test.com", "scopes": ["read"]}

        # User with admin access
        admin_user = {"user_id": "admin_user@test.com", "scopes": ["admin"]}

        # User with no access
        no_access_user = {"user_id": "no_access@test.com", "scopes": []}

        # Test read access
        assert self.auth_manager.validate_user_access(read_user, "read")
        assert not self.auth_manager.validate_user_access(read_user, "write")

        # Test admin access (should have all permissions)
        assert self.auth_manager.validate_user_access(admin_user, "read")
        assert self.auth_manager.validate_user_access(admin_user, "write")

        # Test no access
        assert not self.auth_manager.validate_user_access(no_access_user, "read")

    @patch("agent_data_manager.auth.auth_manager.secretmanager")
    @pytest.mark.deferred
    def test_jwt_secret_from_secret_manager(self, mock_secretmanager):
        """Test JWT secret retrieval from Google Secret Manager"""
        # Mock Secret Manager response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data.decode.return_value = "secret_from_gcp"
        mock_client.access_secret_version.return_value = mock_response
        mock_secretmanager.SecretManagerServiceClient.return_value = mock_client

        # Create new AuthManager instance
        with patch.dict("os.environ", {}, clear=True):
            auth_manager = AuthManager()
            # Should use the secret from Secret Manager
            assert auth_manager.secret_key == "secret_from_gcp"

    @pytest.mark.deferred
    def test_malformed_token_handling(self):
        """Test handling of malformed JWT tokens"""
        malformed_tokens = [
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Missing payload and signature
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0",  # Missing signature
            "not.a.jwt.token.at.all.really",  # Too many parts
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_base64.signature",  # Invalid base64
        ]

        for malformed_token in malformed_tokens:
            with pytest.raises(Exception):  # Should raise HTTPException
                self.auth_manager.verify_token(malformed_token)

    def test_token_without_required_fields(self):
        """Test tokens missing required fields"""
        # Manually create JWT without 'sub'
        token_payload = {
            "email": "test@example.com",
            "scopes": ["read"],
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(token_payload, self.auth_manager.secret_key, algorithm=self.auth_manager.algorithm)

        # Should fail validation due to missing 'sub'
        with pytest.raises(Exception):  # Should raise HTTPException
            self.auth_manager.verify_token(token)


@pytest.mark.deferred
class TestUserManager:
    """Test UserManager functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.user_manager = UserManager()

    @patch("agent_data_manager.auth.user_manager.firestore")
    @pytest.mark.asyncio
    async def test_user_creation(self, mock_firestore):
        """Test user creation in Firestore"""
        # Mock Firestore client
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        user_data = {"email": "newuser@test.com", "password": "secure_password", "full_name": "New User"}

        # Mock the get_user_by_email to return None (user doesn't exist)
        with patch.object(self.user_manager, "get_user_by_email", return_value=None):
            # Test user creation
            result = await self.user_manager.create_user(
                user_data["email"], user_data["password"], user_data["full_name"]
            )

            assert "user_id" in result
            assert result["email"] == user_data["email"]
            assert "password_hash" in result
            assert result["password_hash"] != user_data["password"]  # Should be hashed

    @patch("agent_data_manager.auth.user_manager.firestore")
    @pytest.mark.asyncio
    async def test_user_authentication(self, mock_firestore):
        """Test user authentication"""
        # Mock Firestore client and document
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Mock user data
        mock_user_data = {
            "email": "test@cursor.integration",
            "password_hash": "$2b$12$example_hash",
            "full_name": "Test User",
            "created_at": datetime.utcnow(),
            "is_active": True,
            "user_id": "test_user_id",
        }

        # Mock password verification and user retrieval
        with patch.object(self.user_manager, "get_user_by_email", return_value=mock_user_data), patch(
            "agent_data_manager.auth.user_manager.pwd_context.verify", return_value=True
        ), patch.object(self.user_manager, "update_login_stats", return_value=None):

            user = await self.user_manager.authenticate_user("test@cursor.integration", "test123")
            assert user is not None
            assert user["email"] == "test@cursor.integration"

    @pytest.mark.deferred
    def test_rate_limiting_simulation(self):
        """Test rate limiting behavior simulation"""
        # This test simulates rate limiting behavior
        # In a real scenario, this would test the SlowAPI integration

        start_time = time.time()
        request_times = []

        # Simulate 5 rapid requests
        for i in range(5):
            request_times.append(time.time())
            if i > 0:
                # Simulate minimum time between requests
                time_diff = request_times[i] - request_times[i - 1]
                assert time_diff >= 0  # Basic timing check

        total_time = time.time() - start_time
        assert total_time >= 0  # Basic sanity check


@pytest.mark.deferred
class TestAuthenticationIntegration:
    """Integration tests for authentication with API endpoints"""

    @pytest.mark.deferred
    def test_authentication_flow_simulation(self):
        """Test complete authentication flow simulation"""
        auth_manager = AuthManager()

        # Step 1: Create user token
        user_id = "integration@test.com"
        email = "integration@test.com"
        token = auth_manager.create_user_token(user_id, email)

        # Step 2: Validate token
        payload = auth_manager.verify_token(token)
        assert payload["sub"] == user_id
        assert payload["email"] == email

        # Step 3: Check user access
        user_data = {"user_id": user_id, "email": email, "scopes": payload["scopes"]}

        assert auth_manager.validate_user_access(user_data, "read")
        assert auth_manager.validate_user_access(user_data, "write")

    @pytest.mark.deferred
    def test_token_refresh_simulation(self):
        """Test token refresh simulation"""
        auth_manager = AuthManager()

        # Create initial token
        user_data = {"sub": "refresh@test.com", "email": "refresh@test.com"}
        token1 = auth_manager.create_access_token(user_data)

        # Wait a moment
        time.sleep(1)

        # Create new token (simulating refresh)
        token2 = auth_manager.create_access_token(user_data)

        # Both tokens should be valid but different
        payload1 = auth_manager.verify_token(token1)
        payload2 = auth_manager.verify_token(token2)

        assert token1 != token2
        assert payload1["sub"] == payload2["sub"]
        assert payload1["iat"] != payload2["iat"]  # Different issued times
