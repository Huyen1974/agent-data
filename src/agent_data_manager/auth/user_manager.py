"""
User Manager for Agent Data API A2A Gateway
Handles user storage and retrieval from Firestore
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

from google.cloud import firestore
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserManager:
    """Manages user authentication data in Firestore"""

    def __init__(self, project_id: str = None, database_id: str = "test-default"):
        self.project_id = project_id or "chatgpt-db-project"
        self.database_id = database_id
        self.collection_name = "users"

        try:
            self.firestore_client = firestore.Client(
                project=self.project_id, database=self.database_id
            )
            logger.info(
                f"UserManager initialized with project: {self.project_id}, database: {self.database_id}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email address"""
        try:
            users_ref = self.firestore_client.collection(self.collection_name)
            query = users_ref.where("email", "==", email).limit(1)
            docs = list(query.stream())

            if docs:
                user_data = docs[0].to_dict()
                user_data["user_id"] = docs[0].id
                logger.debug(f"Found user: {email}")
                return user_data
            else:
                logger.debug(f"User not found: {email}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving user {email}: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        """Get user by user ID"""
        try:
            user_ref = self.firestore_client.collection(self.collection_name).document(
                user_id
            )
            user_doc = user_ref.get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_data["user_id"] = user_id
                logger.debug(f"Found user by ID: {user_id}")
                return user_data
            else:
                logger.debug(f"User not found by ID: {user_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {e}")
            return None

    async def create_user(
        self, email: str, password: str, full_name: str = None, scopes: list[str] = None
    ) -> dict[str, Any]:
        """Create a new user"""
        if scopes is None:
            scopes = ["read", "write"]

        # Check if user already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # Hash password
        hashed_password = pwd_context.hash(password)

        # Generate user ID from email hash for consistency
        user_id = hashlib.sha256(email.encode()).hexdigest()[:16]

        user_data = {
            "email": email,
            "password_hash": hashed_password,
            "full_name": full_name or email.split("@")[0],
            "scopes": scopes,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_active": True,
            "login_count": 0,
            "last_login": None,
        }

        try:
            # Create user document
            user_ref = self.firestore_client.collection(self.collection_name).document(
                user_id
            )
            user_ref.set(user_data)

            user_data["user_id"] = user_id
            logger.info(f"Created new user: {email} with ID: {user_id}")
            return user_data

        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise

    async def authenticate_user(
        self, email: str, password: str
    ) -> dict[str, Any] | None:
        """Authenticate user with email and password"""
        try:
            user = await self.get_user_by_email(email)
            if not user:
                logger.warning(f"Authentication failed - user not found: {email}")
                return None

            if not user.get("is_active", True):
                logger.warning(f"Authentication failed - user inactive: {email}")
                return None

            # Verify password
            if not pwd_context.verify(password, user["password_hash"]):
                logger.warning(f"Authentication failed - invalid password: {email}")
                return None

            # Update login statistics
            await self.update_login_stats(user["user_id"])

            logger.info(f"User authenticated successfully: {email}")
            return user

        except Exception as e:
            logger.error(f"Error during authentication for {email}: {e}")
            return None

    async def update_login_stats(self, user_id: str):
        """Update user login statistics"""
        try:
            user_ref = self.firestore_client.collection(self.collection_name).document(
                user_id
            )
            user_ref.update(
                {
                    "last_login": datetime.utcnow(),
                    "login_count": firestore.Increment(1),
                    "updated_at": datetime.utcnow(),
                }
            )
            logger.debug(f"Updated login stats for user: {user_id}")

        except Exception as e:
            logger.error(f"Error updating login stats for {user_id}: {e}")

    async def update_user_scopes(self, user_id: str, scopes: list[str]) -> bool:
        """Update user access scopes"""
        try:
            user_ref = self.firestore_client.collection(self.collection_name).document(
                user_id
            )
            user_ref.update({"scopes": scopes, "updated_at": datetime.utcnow()})
            logger.info(f"Updated scopes for user {user_id}: {scopes}")
            return True

        except Exception as e:
            logger.error(f"Error updating scopes for {user_id}: {e}")
            return False

    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account"""
        try:
            user_ref = self.firestore_client.collection(self.collection_name).document(
                user_id
            )
            user_ref.update({"is_active": False, "updated_at": datetime.utcnow()})
            logger.info(f"Deactivated user: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            return False

    async def list_users(
        self, limit: int = 100, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """List users with optional filtering"""
        try:
            users_ref = self.firestore_client.collection(self.collection_name)

            if active_only:
                users_ref = users_ref.where("is_active", "==", True)

            users_ref = users_ref.limit(limit)

            users = []
            for doc in users_ref.stream():
                user_data = doc.to_dict()
                user_data["user_id"] = doc.id
                # Remove sensitive data
                user_data.pop("password_hash", None)
                users.append(user_data)

            logger.debug(f"Retrieved {len(users)} users")
            return users

        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    async def create_test_user(self) -> dict[str, Any]:
        """Create a test user for development and testing"""
        test_email = "test@cursor.integration"
        test_password = "test123"

        try:
            # Check if test user already exists
            existing_user = await self.get_user_by_email(test_email)
            if existing_user:
                logger.info("Test user already exists")
                return existing_user

            # Create test user
            test_user = await self.create_user(
                email=test_email,
                password=test_password,
                full_name="Test User",
                scopes=["read", "write", "admin"],
            )

            logger.info(f"Created test user: {test_email}")
            return test_user

        except Exception as e:
            logger.error(f"Error creating test user: {e}")
            raise
