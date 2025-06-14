"""
JWT Authentication Manager for Agent Data API A2A Gateway
Handles JWT token generation, validation, and OAuth2 integration
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class AuthManager:
    """Manages JWT authentication for API A2A Gateway"""

    def __init__(self):
        self.secret_key = self._get_jwt_secret()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30

        if not self.secret_key:
            logger.error("JWT_SECRET_KEY not found in environment or Secret Manager")
            raise ValueError("JWT secret key is required for authentication")

    def _get_jwt_secret(self) -> str:
        """Get JWT secret key from environment or Secret Manager"""
        # Try environment variable first
        secret = os.environ.get("JWT_SECRET_KEY")
        if secret:
            return secret

        # Try Google Secret Manager
        try:
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.environ.get("FIRESTORE_PROJECT_ID", "chatgpt-db-project")
            secret_name = f"projects/{project_id}/secrets/jwt-secret-key/versions/latest"

            response = client.access_secret_version(name=secret_name)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not access JWT secret from Secret Manager: {e}")

        # Fallback to a default key for development (NOT for production)
        fallback_key = "development-jwt-secret-key-not-for-production-use-only"
        logger.warning("Using fallback JWT secret key - NOT SECURE FOR PRODUCTION")
        return fallback_key

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "iat": datetime.utcnow()})

        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"Created JWT token for user: {data.get('sub', 'unknown')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create JWT token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create access token"
            )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")

            if user_id is None:
                logger.warning("JWT token missing 'sub' field")
                raise credentials_exception

            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning(f"JWT token expired for user: {user_id}")
                raise credentials_exception

            logger.debug(f"Successfully validated JWT token for user: {user_id}")
            return payload

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise credentials_exception
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise credentials_exception

    async def get_current_user(self, token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
        """Get current user from JWT token (FastAPI dependency)"""
        payload = self.verify_token(token)
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "scopes": payload.get("scopes", []),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
        }

    def create_user_token(self, user_id: str, email: str, scopes: list = None) -> str:
        """Create a JWT token for a specific user"""
        if scopes is None:
            scopes = ["read", "write"]

        token_data = {"sub": user_id, "email": email, "scopes": scopes, "token_type": "access"}

        return self.create_access_token(token_data)

    def validate_user_access(self, user: Dict[str, Any], required_scope: str = "read") -> bool:
        """Validate if user has required access scope"""
        user_scopes = user.get("scopes", [])

        if required_scope in user_scopes or "admin" in user_scopes:
            return True

        logger.warning(f"User {user.get('user_id')} lacks required scope: {required_scope}")
        return False
