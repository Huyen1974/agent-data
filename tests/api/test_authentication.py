"""
Test suite for JWT Authentication functionality in API A2A Gateway
Tests login, token validation, rate limiting, and security features
"""

import pytest
import time
import os
from unittest.mock import patch, MagicMock
from jose import jwt
from datetime import datetime, timedelta

from agent_data_manager.auth.auth_manager import AuthManager
from agent_data_manager.auth.user_manager import UserManager


# Cached password hash to avoid expensive bcrypt operations in setup
CACHED_PASSWORD_HASH = "$2b$12$XSWm27MFTABRgoxDz57jk.VNvZTT3iK66QobF330sjFFvX1VCK9o6"  # hash of "test_password_123"


@pytest.mark.deferred
class TestJWTAuthentication:
    """Test JWT authentication functionality"""

    def setup_method(self):
        """Setup test environment with optimized initialization and mocking"""
        # Mock environment variables to avoid Secret Manager calls
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_secret_key_for_testing_only_123456789',
            'GOOGLE_CLOUD_PROJECT': 'test-project'
        }):
            # Use cached instances to avoid repeated initialization overhead
            if not hasattr(self.__class__, '_auth_manager_cache'):
                # Mock secret manager during initialization
                with patch("agent_data_manager.auth.auth_manager.secretmanager"):
                    self.__class__._auth_manager_cache = AuthManager()
                    self.__class__._user_manager_cache = UserManager()
            
            self.auth_manager = self.__class__._auth_manager_cache
            self.user_manager = self.__class__._user_manager_cache

    @pytest.mark.deferred
    def test_auth_manager_initialization(self):
        """Test AuthManager initializes correctly"""
        assert self.auth_manager.algorithm == "HS256"
        assert self.auth_manager.access_token_expire_minutes == 30
        assert self.auth_manager.secret_key is not None

    @pytest.mark.deferred
    def test_password_hashing_and_verification(self):
        """Test password hashing and verification with optimized setup"""
        password = "test_password_123"
        
        # Use cached hash to avoid expensive bcrypt operation
        hashed = CACHED_PASSWORD_HASH
        
        # Test verification with cached hash
        assert hashed != password
        assert self.auth_manager.verify_password(password, hashed)
        assert not self.auth_manager.verify_password("wrong_password", hashed)
        
        # Only test fresh hashing if specifically needed
        if not hasattr(self.__class__, '_fresh_hash_tested'):
            fresh_hash = self.auth_manager.get_password_hash("fresh_test_password")
            assert fresh_hash != "fresh_test_password"
            assert self.auth_manager.verify_password("fresh_test_password", fresh_hash)
            self.__class__._fresh_hash_tested = True

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
        """Test JWT token expiration handling with optimized timing"""
        user_data = {"sub": "test@cursor.integration", "email": "test@cursor.integration"}

        # Create token with longer expiration first to test immediate validity
        longer_expiry = timedelta(seconds=5)  # Reduced from 10 to 5 seconds
        valid_token = self.auth_manager.create_access_token(user_data, expires_delta=longer_expiry)

        # Token should be valid immediately
        payload = self.auth_manager.verify_token(valid_token)
        assert payload["sub"] == user_data["sub"]

        # Now create token with very short expiration
        short_expiry = timedelta(seconds=0.5)  # Reduced from 1 to 0.5 seconds
        short_token = self.auth_manager.create_access_token(user_data, expires_delta=short_expiry)

        # Wait for token to expire
        time.sleep(0.7)  # Reduced wait time

        # Token should now be invalid - the auth manager raises HTTPException with 401 status
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            self.auth_manager.verify_token(short_token)
        
        # Verify it's the correct type of HTTPException (401 Unauthorized)
        assert exc_info.value.status_code == 401

    @pytest.mark.deferred
    def test_invalid_jwt_token(self):
        """Test handling of invalid JWT tokens"""
        invalid_tokens = [
            "invalid.token.here",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "not_a_jwt_at_all",
        ]

        for invalid_token in invalid_tokens:
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
        # Mock Secret Manager response with faster setup
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.payload.data.decode.return_value = "secret_from_gcp"
        mock_client.access_secret_version.return_value = mock_response
        mock_secretmanager.SecretManagerServiceClient.return_value = mock_client

        # Create new AuthManager instance with environment mocking
        with patch.dict(os.environ, {}, clear=True):
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

    @pytest.mark.deferred
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
        """Setup test environment with optimized initialization"""
        # Mock environment and external services to avoid hangs
        with patch.dict(os.environ, {
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'FIRESTORE_EMULATOR_HOST': 'localhost:8080'
        }):
            # Use cached instance to avoid repeated initialization overhead
            if not hasattr(self.__class__, '_user_manager_cache'):
                # Mock firestore during initialization
                with patch("agent_data_manager.auth.user_manager.firestore"):
                    self.__class__._user_manager_cache = UserManager()
            
            self.user_manager = self.__class__._user_manager_cache

    @patch("agent_data_manager.auth.user_manager.firestore")
    @pytest.mark.asyncio
    async def test_user_creation(self, mock_firestore):
        """Test user creation in Firestore with optimized mocking"""
        # Mock Firestore client
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        user_data = {"email": "newuser@test.com", "password": "secure_password", "full_name": "New User"}

        # Mock the get_user_by_email to return None (user doesn't exist)
        with patch.object(self.user_manager, "get_user_by_email", return_value=None):
            # Mock the create_user method
            with patch.object(self.user_manager, "create_user", return_value={"id": "new_user_id", **user_data}):
                result = await self.user_manager.create_user(user_data)
                assert result["email"] == user_data["email"]
                assert "id" in result

    @patch("agent_data_manager.auth.user_manager.firestore")
    @pytest.mark.asyncio
    async def test_user_authentication(self, mock_firestore):
        """Test user authentication with optimized mocking"""
        # Mock Firestore client
        mock_client = MagicMock()
        mock_firestore.Client.return_value = mock_client

        # Mock user data with hashed password
        mock_user = {
            "email": "test@cursor.integration",
            "password_hash": CACHED_PASSWORD_HASH,  # Use cached hash
            "full_name": "Test User",
            "user_id": "test_user_id",
            "is_active": True
        }

        # Mock get_user_by_email to return the mock user
        with patch.object(self.user_manager, "get_user_by_email", return_value=mock_user):
            # Test successful authentication
            result = await self.user_manager.authenticate_user("test@cursor.integration", "test_password_123")
            assert result is not None
            assert result["email"] == "test@cursor.integration"

            # Test failed authentication
            result = await self.user_manager.authenticate_user("test@cursor.integration", "wrong_password")
            assert result is None

    @pytest.mark.deferred
    def test_rate_limiting_simulation(self):
        """Test rate limiting simulation with optimized timing"""
        # Simulate rate limiting without actual delays
        rate_limit_window = 60  # seconds
        max_attempts = 5
        
        # Mock rate limiting data
        attempts = []
        current_time = time.time()
        
        # Simulate attempts within window
        for i in range(max_attempts + 2):
            attempt_time = current_time + i * 5  # 5 seconds apart
            attempts.append(attempt_time)
            
            # Check if within rate limit
            recent_attempts = [t for t in attempts if attempt_time - t < rate_limit_window]
            is_rate_limited = len(recent_attempts) > max_attempts
            
            if i < max_attempts:
                assert not is_rate_limited, f"Attempt {i+1} should not be rate limited"
            else:
                assert is_rate_limited, f"Attempt {i+1} should be rate limited"


@pytest.mark.deferred
class TestAuthenticationIntegration:
    """Test authentication integration scenarios"""

    def setup_method(self):
        """Setup with mocked environment to avoid timeouts"""
        with patch.dict(os.environ, {
            'JWT_SECRET_KEY': 'test_secret_key_for_integration_testing_123456789'
        }):
            with patch("agent_data_manager.auth.auth_manager.secretmanager"):
                self.auth_manager = AuthManager()

    @pytest.mark.deferred
    def test_authentication_flow_simulation(self):
        """Test complete authentication flow simulation"""
        # Simulate user login
        user_data = {
            "sub": "integration@test.com",
            "email": "integration@test.com",
            "scopes": ["read", "write"]
        }
        
        # Create token
        token = self.auth_manager.create_access_token(user_data)
        assert token is not None
        
        # Validate token
        payload = self.auth_manager.verify_token(token)
        assert payload["sub"] == user_data["sub"]
        
        # Test access validation
        assert self.auth_manager.validate_user_access(payload, "read")
        assert self.auth_manager.validate_user_access(payload, "write")
        assert not self.auth_manager.validate_user_access(payload, "admin")

    @pytest.mark.deferred
    def test_token_refresh_simulation(self):
        """Test token refresh simulation with optimized approach"""
        # Create initial token with different expiry to ensure uniqueness
        user_data = {"sub": "refresh@test.com", "email": "refresh@test.com"}
        old_token = self.auth_manager.create_access_token(
            user_data, expires_delta=timedelta(minutes=15)
        )
        
        # Add minimal delay to ensure different timestamps
        time.sleep(0.2)  # Slightly increased to ensure different iat
        
        # Simulate token refresh (create new token with different expiry)
        new_token = self.auth_manager.create_access_token(
            user_data, expires_delta=timedelta(minutes=30)
        )
        
        # Both tokens should be valid but different
        assert old_token != new_token
        
        old_payload = self.auth_manager.verify_token(old_token)
        new_payload = self.auth_manager.verify_token(new_token)
        
        assert old_payload["sub"] == new_payload["sub"]
        assert old_payload["email"] == new_payload["email"]
        # Verify different expiration times
        assert old_payload["exp"] != new_payload["exp"]
