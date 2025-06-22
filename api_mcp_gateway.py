"""
FastAPI-based API A2A Gateway for Agent-to-Agent Communication
Provides REST endpoints for document saving, querying, and semantic search
"""

import logging
import os
import asyncio
import hashlib
import threading
import time
from collections import OrderedDict
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, Field
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import Agent Data components
from ADK.agent_data.vector_store.qdrant_store import QdrantStore
from ADK.agent_data.vector_store.firestore_metadata_manager import FirestoreMetadataManager
from ADK.agent_data.tools.qdrant_vectorization_tool import QdrantVectorizationTool, qdrant_rag_search
from ADK.agent_data.config.settings import settings
from ADK.agent_data.auth.auth_manager import AuthManager
from ADK.agent_data.auth.user_manager import UserManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Enhanced LRU Cache implementation (CLI 140e)
class ThreadSafeLRUCache:
    """Thread-safe LRU cache with TTL support and configurable size."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._lock = threading.RLock()

    def _is_expired(self, timestamp: float) -> bool:
        """Check if a cache entry is expired."""
        return time.time() - timestamp > self.ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, return None if not found or expired."""
        with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]

            if self._is_expired(timestamp):
                del self._cache[key]
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return value

    def put(self, key: str, value: Any) -> None:
        """Put value in cache with current timestamp."""
        with self._lock:
            current_time = time.time()

            if key in self._cache:
                # Update existing entry
                self._cache[key] = (value, current_time)
                self._cache.move_to_end(key)
            else:
                # Add new entry
                self._cache[key] = (value, current_time)

                # Evict oldest entries if over max size
                while len(self._cache) > self.max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)

    def cleanup_expired(self) -> int:
        """Remove expired entries and return count of removed entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, (value, timestamp) in self._cache.items():
                if current_time - timestamp > self.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

            return len(expired_keys)


# Global cache instances
_rag_cache: Optional[ThreadSafeLRUCache] = None
_embedding_cache: Optional[ThreadSafeLRUCache] = None


def _get_cache_key(query_text: str, **kwargs) -> str:
    """Generate MD5 hash cache key from query parameters."""
    # Create a consistent string representation of all parameters
    params = {"query_text": query_text}
    params.update(kwargs)

    # Sort parameters for consistent hashing
    sorted_params = sorted(params.items())
    param_string = str(sorted_params)

    # Generate MD5 hash
    return hashlib.md5(param_string.encode()).hexdigest()


def _get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached result from RAG cache."""
    global _rag_cache
    if not _rag_cache or not settings.RAG_CACHE_ENABLED:
        return None
    return _rag_cache.get(cache_key)


def _cache_result(cache_key: str, result: Dict[str, Any]) -> None:
    """Cache result in RAG cache."""
    global _rag_cache
    if not _rag_cache or not settings.RAG_CACHE_ENABLED:
        return
    _rag_cache.put(cache_key, result)


def _initialize_caches():
    """Initialize cache instances with configuration from settings."""
    global _rag_cache, _embedding_cache

    cache_config = settings.get_cache_config()

    if cache_config["rag_cache_enabled"]:
        _rag_cache = ThreadSafeLRUCache(
            max_size=cache_config["rag_cache_max_size"], ttl_seconds=cache_config["rag_cache_ttl"]
        )
        logger.info(
            f"Initialized RAG cache: max_size={cache_config['rag_cache_max_size']}, ttl={cache_config['rag_cache_ttl']}s"
        )

    if cache_config["embedding_cache_enabled"]:
        _embedding_cache = ThreadSafeLRUCache(
            max_size=cache_config["embedding_cache_max_size"], ttl_seconds=cache_config["embedding_cache_ttl"]
        )
        logger.info(
            f"Initialized embedding cache: max_size={cache_config['embedding_cache_max_size']}, ttl={cache_config['embedding_cache_ttl']}s"
        )


def initialize_caches():
    """Public function to initialize caches - exposed for testing."""
    return _initialize_caches()


# Custom rate limiting key function for Cloud Run
def get_user_id_for_rate_limiting(request: Request):
    """
    Custom key function for rate limiting that uses user ID from JWT token.
    Falls back to IP address for unauthenticated endpoints.
    """
    try:
        # Try to get user ID from JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # We'll decode the token to get user ID
            # For now, use a simple approach - in production, decode JWT properly
            import base64
            import json

            try:
                # Decode JWT payload (this is a simplified approach)
                payload_part = token.split(".")[1]
                # Add padding if needed
                payload_part += "=" * (4 - len(payload_part) % 4)
                payload = json.loads(base64.b64decode(payload_part))
                user_id = payload.get("sub", "unknown_user")
                logger.info(f"Rate limiting key: user_id={user_id}")
                return f"user:{user_id}"
            except Exception as e:
                logger.warning(f"Failed to decode JWT for rate limiting: {e}")
                pass
    except Exception as e:
        logger.warning(f"Error getting user ID for rate limiting: {e}")

    # Fallback to IP address
    remote_addr = get_remote_address(request)
    logger.info(f"Rate limiting key: ip={remote_addr}")
    return f"ip:{remote_addr}"


# Initialize rate limiter for free tier constraints
limiter = Limiter(key_func=get_user_id_for_rate_limiting)

# Initialize FastAPI app
app = FastAPI(
    title="Agent Data API A2A Gateway",
    description="REST API for agent-to-agent communication with Qdrant and Firestore",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (initialized on startup)
qdrant_store: Optional[QdrantStore] = None
firestore_manager: Optional[FirestoreMetadataManager] = None
vectorization_tool: Optional[QdrantVectorizationTool] = None
auth_manager: Optional[AuthManager] = None
user_manager: Optional[UserManager] = None

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


# Pydantic models for API requests/responses
class SaveDocumentRequest(BaseModel):
    doc_id: str = Field(..., min_length=1, description="Unique document identifier")
    content: str = Field(..., min_length=1, description="Document content to vectorize and store")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Optional metadata")
    tag: Optional[str] = Field(default=None, description="Optional tag for grouping")
    update_firestore: bool = Field(default=True, description="Whether to update Firestore metadata")


class SaveDocumentResponse(BaseModel):
    status: str
    doc_id: str
    message: str
    vector_id: Optional[str] = None
    embedding_dimension: Optional[int] = None
    firestore_updated: bool = False
    error: Optional[str] = None


class QueryVectorsRequest(BaseModel):
    query_text: str = Field(..., description="Text to search for semantically similar documents")
    tag: Optional[str] = Field(default=None, description="Optional tag filter")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    score_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class QueryVectorsResponse(BaseModel):
    status: str
    query_text: str
    results: List[Dict[str, Any]]
    total_found: int
    message: str
    error: Optional[str] = None


class SearchDocumentsRequest(BaseModel):
    tag: Optional[str] = Field(default=None, description="Tag to filter documents")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    include_vectors: bool = Field(default=False, description="Whether to include vector embeddings")


class SearchDocumentsResponse(BaseModel):
    status: str
    results: List[Dict[str, Any]]
    total_found: int
    offset: int
    limit: int
    message: str
    error: Optional[str] = None


# CLI140e RAG endpoint models
class RAGSearchRequest(BaseModel):
    query_text: str = Field(..., description="Text to search for using hybrid RAG")
    metadata_filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")
    tags: Optional[List[str]] = Field(default=None, description="Tag filters")
    path_query: Optional[str] = Field(default=None, description="Path query filter")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    qdrant_tag: Optional[str] = Field(default=None, description="Qdrant tag filter")


class RAGSearchResponse(BaseModel):
    status: str
    query: str
    results: List[Dict[str, Any]]
    count: int
    rag_info: Dict[str, Any]
    message: str
    error: Optional[str] = None


class LoginRequest(BaseModel):
    username: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    email: str
    scopes: List[str]


class UserRegistrationRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password (minimum 6 characters)")
    full_name: Optional[str] = Field(default=None, description="User full name")


class UserRegistrationResponse(BaseModel):
    status: str
    message: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]
    authentication: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize connections to Qdrant, Firestore, and Authentication on startup"""
    global qdrant_store, firestore_manager, vectorization_tool, auth_manager, user_manager

    logger.info("Initializing API A2A Gateway services...")

    try:
        # Initialize Authentication Manager
        if settings.ENABLE_AUTHENTICATION:
            auth_manager = AuthManager()
            logger.info("AuthManager initialized successfully")

            # Initialize User Manager
            firestore_config = settings.get_firestore_config()
            user_manager = UserManager(
                project_id=firestore_config.get("project_id"), database_id=firestore_config.get("database_id")
            )
            logger.info("UserManager initialized successfully")

            # Create test user for development
            try:
                await user_manager.create_test_user()
            except Exception as e:
                logger.info(f"Test user creation: {e}")

        # Initialize QdrantStore
        qdrant_config = settings.get_qdrant_config()
        qdrant_store = QdrantStore(
            url=qdrant_config["url"],
            api_key=qdrant_config["api_key"],
            collection_name=qdrant_config["collection_name"],
            vector_size=qdrant_config["vector_size"],
        )
        logger.info("QdrantStore initialized successfully")

        # Initialize FirestoreMetadataManager
        firestore_config = settings.get_firestore_config()
        firestore_manager = FirestoreMetadataManager(
            project_id=firestore_config.get("project_id"),
            collection_name=firestore_config.get("metadata_collection", "document_metadata"),
        )
        logger.info("FirestoreMetadataManager initialized successfully")

        # Initialize QdrantVectorizationTool
        vectorization_tool = QdrantVectorizationTool()
        logger.info("QdrantVectorizationTool initialized successfully")

        # Initialize caches
        _initialize_caches()

        logger.info("API A2A Gateway startup completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize API A2A Gateway: {e}")
        raise


# Authentication dependency
async def get_current_user_dependency():
    """Create the current user dependency"""
    if not settings.ENABLE_AUTHENTICATION:
        # If authentication is disabled, return a default user
        return {
            "user_id": "anonymous",
            "email": "anonymous@system",
            "scopes": ["read", "write"],
        }

    if not auth_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service unavailable"
        )

    return await auth_manager.get_current_user()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Get current user dependency function"""
    if not settings.ENABLE_AUTHENTICATION:
        return {"user_id": "anonymous", "email": "anonymous@system", "scopes": ["read", "write"]}

    if not auth_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service unavailable"
        )

    # Use the auth_manager to verify token
    payload = auth_manager.verify_token(token)
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "scopes": payload.get("scopes", []),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    services = {
        "qdrant": "connected" if qdrant_store else "disconnected",
        "firestore": "connected" if firestore_manager else "disconnected",
        "vectorization": "available" if vectorization_tool else "unavailable",
    }

    auth_status = {
        "enabled": settings.ENABLE_AUTHENTICATION,
        "auth_manager": "available" if auth_manager else "unavailable",
        "user_manager": "available" if user_manager else "unavailable",
        "registration_allowed": settings.ALLOW_REGISTRATION,
    }

    return HealthResponse(
        status="healthy" if all(v == "connected" or v == "available" for v in services.values()) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0",
        services=services,
        authentication=auth_status,
    )


@app.post("/auth/login", response_model=LoginResponse)
@limiter.limit("5/minute")  # Strict rate limit for authentication
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT token"""
    if not settings.ENABLE_AUTHENTICATION:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Authentication is disabled")

    if not user_manager or not auth_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication services unavailable"
        )

    try:
        # Authenticate user
        user = await user_manager.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token = auth_manager.create_user_token(
            user_id=user["user_id"], email=user["email"], scopes=user.get("scopes", ["read", "write"])
        )

        logger.info(f"User logged in successfully: {user['email']}")

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=auth_manager.access_token_expire_minutes * 60,
            user_id=user["user_id"],
            email=user["email"],
            scopes=user.get("scopes", ["read", "write"]),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal authentication error")


@app.post("/auth/register", response_model=UserRegistrationResponse)
@limiter.limit("3/minute")  # Very strict rate limit for registration
async def register(request: Request, registration_data: UserRegistrationRequest):
    """Register a new user"""
    if not settings.ENABLE_AUTHENTICATION:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Authentication is disabled")

    if not settings.ALLOW_REGISTRATION:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User registration is not allowed")

    if not user_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User management service unavailable"
        )

    try:
        # Create new user
        user = await user_manager.create_user(
            email=registration_data.email,
            password=registration_data.password,
            full_name=registration_data.full_name,
            scopes=["read", "write"],  # Default scopes for new users
        )

        logger.info(f"New user registered: {registration_data.email}")

        return UserRegistrationResponse(
            status="success", message="User registered successfully", user_id=user["user_id"], email=user["email"]
        )

    except ValueError as e:
        return UserRegistrationResponse(status="failed", message="Registration failed", error=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return UserRegistrationResponse(status="error", message="Internal registration error", error=str(e))


@app.post("/save", response_model=SaveDocumentResponse)
@limiter.limit("10/minute")  # Rate limit for free tier
async def save_document(
    request: Request,
    document_data: SaveDocumentRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Save and vectorize a document for agent-to-agent access
    """
    if not vectorization_tool:
        raise HTTPException(status_code=503, detail="Vectorization service unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to save documents")

    try:
        logger.info(
            f"Processing save request for doc_id: {document_data.doc_id} by user: {current_user.get('user_id', 'anonymous')}"
        )

        # Add API source metadata with user information
        enhanced_metadata = {
            **document_data.metadata,
            "api_source": "a2a_gateway",
            "received_at": datetime.utcnow().isoformat(),
            "content_length": len(document_data.content),
            "user_id": current_user.get("user_id"),
            "user_email": current_user.get("email"),
        }

        # Use vectorization tool to process the document
        result = await vectorization_tool.vectorize_document(
            doc_id=document_data.doc_id,
            content=document_data.content,
            metadata=enhanced_metadata,
            tag=document_data.tag,
            update_firestore=document_data.update_firestore,
        )

        if result.get("status") == "success":
            return SaveDocumentResponse(
                status="success",
                doc_id=document_data.doc_id,
                message=f"Document {document_data.doc_id} saved and vectorized successfully",
                vector_id=result.get("vector_id"),
                embedding_dimension=result.get("embedding_dimension"),
                firestore_updated=document_data.update_firestore,
            )
        else:
            return SaveDocumentResponse(
                status="failed",
                doc_id=document_data.doc_id,
                message=f"Failed to save document {document_data.doc_id}",
                error=result.get("error"),
            )

    except Exception as e:
        logger.error(f"Error saving document {document_data.doc_id}: {e}")
        return SaveDocumentResponse(
            status="error",
            doc_id=document_data.doc_id,
            message=f"Internal error saving document {document_data.doc_id}",
            error=str(e),
        )


@app.post("/query", response_model=QueryVectorsResponse)
@limiter.limit("20/minute")  # Higher limit for queries
async def query_vectors(
    request: Request, query_data: QueryVectorsRequest, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Perform semantic search on vectorized documents with CLI140e optimizations
    Target latency: <0.5s
    """
    if not qdrant_store:
        raise HTTPException(status_code=503, detail="Qdrant service unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to query documents")

    try:
        # CLI140e Optimization: Check cache first
        cache_key = _get_cache_key(
            query_data.query_text,
            tag=query_data.tag,
            limit=query_data.limit,
            score_threshold=query_data.score_threshold
        )
        
        cached_result = _get_cached_result(cache_key)
        if cached_result:
            logger.info(f"Cache hit for query: {query_data.query_text[:30]}...")
            return QueryVectorsResponse(
                status="success",
                query_text=query_data.query_text,
                results=cached_result.get("results", []),
                total_found=len(cached_result.get("results", [])),
                message=f"Found {len(cached_result.get('results', []))} results for semantic query (cached)",
            )

        # Log rate limiting information
        rate_limit_key = get_user_id_for_rate_limiting(request)
        logger.info(f"Query request from rate limit key: {rate_limit_key}")
        logger.info(
            f"Processing semantic query: {query_data.query_text[:50]}... by user: {current_user.get('user_id', 'anonymous')}"
        )

        # CLI140e Optimization: Use timeout and optimized search
        start_time = time.time()
        search_results = await asyncio.wait_for(
            qdrant_store.semantic_search(
                query_text=query_data.query_text,
                limit=query_data.limit,
                tag=query_data.tag,
                score_threshold=query_data.score_threshold,
            ),
            timeout=0.4  # 0.4s timeout to ensure <0.5s total response
        )
        
        query_latency = time.time() - start_time
        
        # Cache the result for future requests
        result_data = {"results": search_results.get("results", [])}
        _cache_result(cache_key, result_data)
        
        logger.info(f"Semantic query completed in {query_latency:.3f}s")

        return QueryVectorsResponse(
            status="success",
            query_text=query_data.query_text,
            results=search_results.get("results", []),
            total_found=len(search_results.get("results", [])),
            message=f"Found {len(search_results.get('results', []))} results for semantic query",
        )

    except asyncio.TimeoutError:
        logger.warning(f"Query timeout for: {query_data.query_text[:30]}...")
        return QueryVectorsResponse(
            status="timeout",
            query_text=query_data.query_text,
            results=[],
            total_found=0,
            message="Query timeout - please try with more specific terms",
            error="Query exceeded timeout limit",
        )
    except Exception as e:
        logger.error(f"Error performing semantic query: {e}")
        return QueryVectorsResponse(
            status="error",
            query_text=query_data.query_text,
            results=[],
            total_found=0,
            message="Internal error during semantic search",
            error=str(e),
        )


@app.post("/search", response_model=SearchDocumentsResponse)
@limiter.limit("30/minute")  # Higher limit for search
async def search_documents(
    request: Request, search_data: SearchDocumentsRequest, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Search documents by tag and metadata filters
    """
    if not qdrant_store:
        raise HTTPException(status_code=503, detail="Qdrant service unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to search documents"
        )

    try:
        logger.info(
            f"Processing document search with tag: {search_data.tag} by user: {current_user.get('user_id', 'anonymous')}"
        )

        # Use QdrantStore to search by tag
        if search_data.tag:
            search_results = await qdrant_store.query_vectors_by_tag(
                tag=search_data.tag, offset=search_data.offset, limit=search_data.limit
            )
        else:
            # If no tag specified, get recent documents
            search_results = await qdrant_store.get_recent_documents(limit=search_data.limit, offset=search_data.offset)

        # Process results to include/exclude vectors as requested
        processed_results = []
        for result in search_results.get("results", []):
            processed_result = result.copy()
            if not search_data.include_vectors and "vector" in processed_result:
                del processed_result["vector"]
            processed_results.append(processed_result)

        return SearchDocumentsResponse(
            status="success",
            results=processed_results,
            total_found=len(processed_results),
            offset=search_data.offset,
            limit=search_data.limit,
            message=f"Found {len(processed_results)} documents",
        )

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return SearchDocumentsResponse(
            status="error",
            results=[],
            total_found=0,
            offset=search_data.offset,
            limit=search_data.limit,
            message="Internal error during document search",
            error=str(e),
        )


@app.post("/rag", response_model=RAGSearchResponse)
@limiter.limit("30/minute")  # Higher limit for RAG
async def rag_search(
    request: Request, search_data: RAGSearchRequest, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Perform hybrid RAG search on vectorized documents with CLI140e optimizations
    Target latency: <0.5s
    """
    if not qdrant_store:
        raise HTTPException(status_code=503, detail="Qdrant service unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to query documents")

    try:
        logger.info(
            f"Processing RAG search with query: {search_data.query_text[:50]}... by user: {current_user.get('user_id', 'anonymous')}"
        )

        # CLI140e Optimization: Use timeout and optimized RAG search
        start_time = time.time()
        search_results = await asyncio.wait_for(
            qdrant_rag_search(
                query_text=search_data.query_text,
                metadata_filters=search_data.metadata_filters,
                tags=search_data.tags,
                path_query=search_data.path_query,
                limit=search_data.limit,
                score_threshold=search_data.score_threshold,
                qdrant_tag=search_data.qdrant_tag,
            ),
            timeout=0.6  # 0.6s timeout for RAG (more complex than simple search)
        )
        
        query_latency = time.time() - start_time
        
        # Cache the result for future requests
        result_data = {"results": search_results.get("results", [])}
        _cache_result(search_data.query_text, result_data)
        
        logger.info(f"RAG search completed in {query_latency:.3f}s")

        return RAGSearchResponse(
            status="success",
            query=search_data.query_text,
            results=search_results.get("results", []),
            count=len(search_results.get("results", [])),
            rag_info=search_results.get("rag_info", {"latency": query_latency}),
            message=f"Found {len(search_results.get('results', []))} results for RAG query",
        )

    except asyncio.TimeoutError:
        logger.warning(f"RAG timeout for: {search_data.query_text[:30]}...")
        return RAGSearchResponse(
            status="timeout",
            query=search_data.query_text,
            results=[],
            count=0,
            rag_info={"latency": 0.6, "timeout": True},
            message="RAG query timeout - please try with more specific terms",
            error="Query exceeded timeout limit",
        )
    except Exception as e:
        logger.error(f"Error performing RAG search: {e}")
        return RAGSearchResponse(
            status="error",
            query=search_data.query_text,
            results=[],
            count=0,
            rag_info={"latency": 0.4},
            message="Internal error during RAG search",
            error=str(e),
        )


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Agent Data API A2A Gateway",
        "version": "1.0.0",
        "description": "REST API for agent-to-agent communication with JWT authentication",
        "endpoints": {
            "health": "/health",
            "auth": {
                "login": "/auth/login",
                "register": "/auth/register" if settings.ALLOW_REGISTRATION else "disabled",
            },
            "api": {"save": "/save", "query": "/query", "search": "/search", "rag": "/rag"},
            "docs": "/docs",
        },
        "authentication": {
            "enabled": settings.ENABLE_AUTHENTICATION,
            "registration_allowed": settings.ALLOW_REGISTRATION,
            "token_type": "Bearer JWT",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


def main():
    """Main entry point for running the API server"""
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")

    logger.info(f"Starting Agent Data API A2A Gateway on {host}:{port}")

    uvicorn.run(
        "ADK.agent_data.api_mcp_gateway:app",
        host=host,
        port=port,
        reload=False,  # Set to True for development
        access_log=True,
    )


if __name__ == "__main__":
    main()
