"""Agent Data configuration settings."""

import os


class Settings:
    """Configuration settings for Agent Data system."""

    # Vector backend configuration
    VECTOR_BACKEND: str = "QDRANT"

    # Qdrant configuration
    QDRANT_URL: str = os.environ.get(
        "QDRANT_URL",
        "https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io",
    )
    QDRANT_API_KEY: str = os.environ.get("QDRANT_API_KEY", "")
    QDRANT_COLLECTION_NAME: str = os.environ.get(
        "QDRANT_COLLECTION_NAME", "agent_data_vectors"
    )
    QDRANT_REGION: str = "us-east4-0"  # Free tier region

    # Vector configuration
    VECTOR_DIMENSION: int = int(
        os.environ.get("VECTOR_DIMENSION", "1536")
    )  # OpenAI default

    # Qdrant batch processing configuration
    QDRANT_BATCH_SIZE: int = int(os.environ.get("QDRANT_BATCH_SIZE", "100"))
    QDRANT_SLEEP: float = float(
        os.environ.get("QDRANT_SLEEP", "0.35")
    )  # Sleep between batches in seconds

    # JWT Authentication configuration
    JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Authentication configuration
    ENABLE_AUTHENTICATION: bool = (
        os.environ.get("ENABLE_AUTHENTICATION", "true").lower() == "true"
    )
    ALLOW_REGISTRATION: bool = (
        os.environ.get("ALLOW_REGISTRATION", "false").lower() == "true"
    )

    # Prometheus metrics configuration
    PUSHGATEWAY_URL: str = os.environ.get(
        "PUSHGATEWAY_URL",
        "https://prometheus-pushgateway-812872501910.asia-southeast1.run.app",
    )
    METRICS_PUSH_INTERVAL: int = int(
        os.environ.get("METRICS_PUSH_INTERVAL", "60")
    )  # seconds
    ENABLE_METRICS: bool = os.environ.get("ENABLE_METRICS", "true").lower() == "true"

    # Firestore configuration
    ENABLE_FIRESTORE_SYNC: bool = (
        os.environ.get("ENABLE_FIRESTORE_SYNC", "false").lower() == "true"
    )
    FIRESTORE_PROJECT_ID: str = os.environ.get(
        "FIRESTORE_PROJECT_ID", "github-chatgpt-ggcloud"
    )
    FIRESTORE_DATABASE_ID: str = os.environ.get("FIRESTORE_DATABASE_ID", "test-default")

    # GCS configuration
    GCS_BUCKET_NAME: str = os.environ.get("GCS_BUCKET_NAME", "qdrant-snapshots")

    # Embedding configuration
    EMBEDDING_PROVIDER: str = os.environ.get("EMBEDDING_PROVIDER", "openai")
    OPENAI_EMBEDDING_MODEL: str = os.environ.get(
        "OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"
    )

    # Cache configuration for performance optimization (CLI 140e)
    RAG_CACHE_ENABLED: bool = (
        os.environ.get("RAG_CACHE_ENABLED", "true").lower() == "true"
    )
    RAG_CACHE_TTL: int = int(
        os.environ.get("RAG_CACHE_TTL", "3600")
    )  # 1 hour in seconds
    RAG_CACHE_MAX_SIZE: int = int(
        os.environ.get("RAG_CACHE_MAX_SIZE", "1000")
    )  # Max cache entries
    EMBEDDING_CACHE_ENABLED: bool = (
        os.environ.get("EMBEDDING_CACHE_ENABLED", "true").lower() == "true"
    )
    EMBEDDING_CACHE_TTL: int = int(
        os.environ.get("EMBEDDING_CACHE_TTL", "3600")
    )  # 1 hour in seconds
    EMBEDDING_CACHE_MAX_SIZE: int = int(
        os.environ.get("EMBEDDING_CACHE_MAX_SIZE", "500")
    )  # Max cache entries

    @classmethod
    def get_embedding_config(cls) -> dict:
        """Get embedding configuration dictionary."""
        return {
            "provider": cls.EMBEDDING_PROVIDER,
            "openai_model": cls.OPENAI_EMBEDDING_MODEL,
        }

    @classmethod
    def get_qdrant_config(cls) -> dict:
        """Get Qdrant configuration dictionary."""
        return {
            "url": cls.QDRANT_URL,
            "api_key": cls.QDRANT_API_KEY,
            "collection_name": cls.QDRANT_COLLECTION_NAME,
            "vector_size": cls.VECTOR_DIMENSION,
            "region": cls.QDRANT_REGION,
            "batch_size": cls.QDRANT_BATCH_SIZE,
            "sleep_between_batches": cls.QDRANT_SLEEP,
        }

    @classmethod
    def get_jwt_config(cls) -> dict:
        """Get JWT configuration dictionary."""
        return {
            "secret_key": cls.JWT_SECRET_KEY,
            "algorithm": cls.JWT_ALGORITHM,
            "access_token_expire_minutes": cls.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            "enabled": cls.ENABLE_AUTHENTICATION,
            "allow_registration": cls.ALLOW_REGISTRATION,
        }

    @classmethod
    def get_metrics_config(cls) -> dict:
        """Get metrics configuration dictionary."""
        return {
            "pushgateway_url": cls.PUSHGATEWAY_URL,
            "push_interval": cls.METRICS_PUSH_INTERVAL,
            "enabled": cls.ENABLE_METRICS,
        }

    @classmethod
    def get_firestore_config(cls) -> dict:
        """Get Firestore configuration dictionary."""
        return {
            "enabled": cls.ENABLE_FIRESTORE_SYNC,
            "project_id": cls.FIRESTORE_PROJECT_ID,
            "database_id": cls.FIRESTORE_DATABASE_ID,
            "metadata_collection": "document_metadata",
            "users_collection": "users",
        }

    @classmethod
    def validate_qdrant_config(cls) -> bool:
        """Validate that required Qdrant configuration is present."""
        if not cls.QDRANT_URL:
            return False
        if not cls.QDRANT_API_KEY:
            return False
        return True

    @classmethod
    def validate_jwt_config(cls) -> bool:
        """Validate that required JWT configuration is present."""
        if cls.ENABLE_AUTHENTICATION and not cls.JWT_SECRET_KEY:
            return False
        return True

    @classmethod
    def get_cache_config(cls) -> dict:
        """Get cache configuration dictionary for performance optimization."""
        return {
            "rag_cache_enabled": cls.RAG_CACHE_ENABLED,
            "rag_cache_ttl": cls.RAG_CACHE_TTL,
            "rag_cache_max_size": cls.RAG_CACHE_MAX_SIZE,
            "embedding_cache_enabled": cls.EMBEDDING_CACHE_ENABLED,
            "embedding_cache_ttl": cls.EMBEDDING_CACHE_TTL,
            "embedding_cache_max_size": cls.EMBEDDING_CACHE_MAX_SIZE,
        }


# Global settings instance
settings = Settings()
