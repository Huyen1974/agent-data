"""
FastAPI-based API A2A Gateway for Agent-to-Agent Communication
Provides REST endpoints for document saving, querying, and semantic search
"""

import asyncio
import logging
import os
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

# Import retry logic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import Agent Data components
from agent_data_manager.vector_store.qdrant_store import QdrantStore
from agent_data_manager.vector_store.firestore_metadata_manager import FirestoreMetadataManager
from agent_data_manager.tools.qdrant_vectorization_tool import QdrantVectorizationTool, qdrant_rag_search
from agent_data_manager.config.settings import settings
from agent_data_manager.auth.auth_manager import AuthManager
from agent_data_manager.auth.user_manager import UserManager
from agent_data_manager.tools.prometheus_metrics import (
    # record_qdrant_request,  # Unused import
    record_semantic_search,
    MetricsTimer,
    record_a2a_api_request,
    record_a2a_api_error,
    record_rag_search,
    record_cskh_query,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Enhanced LRU cache for RAG optimization (CLI 140e)


class LRUCache:
    """Thread-safe LRU cache with TTL support for performance optimization."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()

    def get(self, key: str):
        """Get item from cache, return None if not found or expired."""
        with self.lock:
            if key not in self.cache:
                return None

            # Check TTL
            if time.time() - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key: str, value):
        """Put item in cache, evict oldest if necessary."""
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            else:
                if len(self.cache) >= self.max_size:
                    # Remove oldest item
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]

            self.cache[key] = value
            self.timestamps[key] = time.time()

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self.lock:
            return len(self.cache)


# Initialize enhanced cache
_rag_cache = LRUCache(max_size=settings.RAG_CACHE_MAX_SIZE, ttl=settings.RAG_CACHE_TTL)


# Enhanced error classes for better error categorization
class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""

    pass


class ValidationError(Exception):
    """Raised when input validation fails"""

    pass


class ServerError(Exception):
    """Raised when server encounters internal errors"""

    pass


class TimeoutError(Exception):
    """Raised when operation times out"""

    pass


# Retry decorator for API operations
def api_retry(max_attempts: int = 3):
    """Decorator for API operations with exponential backoff retry logic"""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2.0),
        retry=retry_if_exception_type((RateLimitError, ServerError, TimeoutError)),
        reraise=True,
    )


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


# New Batch Operation Models
class BatchSaveRequest(BaseModel):
    documents: List[SaveDocumentRequest] = Field(
        ..., min_length=1, max_length=50, description="List of documents to save (max 50)"
    )
    batch_id: Optional[str] = Field(default=None, description="Optional batch identifier")


class BatchSaveResponse(BaseModel):
    status: str
    batch_id: Optional[str] = None
    total_documents: int
    successful_saves: int
    failed_saves: int
    results: List[SaveDocumentResponse]
    message: str
    error: Optional[str] = None


class BatchQueryRequest(BaseModel):
    queries: List[QueryVectorsRequest] = Field(
        ..., min_length=1, max_length=20, description="List of queries to execute (max 20)"
    )
    batch_id: Optional[str] = Field(default=None, description="Optional batch identifier")


class BatchQueryResponse(BaseModel):
    status: str
    batch_id: Optional[str] = None
    total_queries: int
    successful_queries: int
    failed_queries: int
    results: List[QueryVectorsResponse]
    message: str
    error: Optional[str] = None


class CSKHQueryRequest(BaseModel):
    """Request model for CSKH (Customer Care) Agent queries with contextual filtering."""

    query_text: str = Field(..., min_length=1, description="Customer care query text")
    customer_context: Optional[Dict[str, Any]] = Field(
        default={}, description="Customer context (e.g., customer_id, account_type, issue_category)"
    )
    metadata_filters: Optional[Dict[str, Any]] = Field(default={}, description="Metadata filters for contextual search")
    tags: Optional[List[str]] = Field(default=[], description="Tags to filter relevant knowledge base content")
    path_query: Optional[str] = Field(default=None, description="Hierarchical path query for knowledge organization")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    score_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum similarity score")
    include_context: bool = Field(default=True, description="Include customer context in response")


class CSKHQueryResponse(BaseModel):
    """Response model for CSKH Agent queries with enriched results."""

    status: str
    query_text: str
    customer_context: Dict[str, Any]
    results: List[Dict[str, Any]]
    total_found: int
    rag_info: Dict[str, Any]
    response_time_ms: float
    cached: bool = False
    message: str
    error: Optional[str] = None


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
    """Get current user from JWT token"""
    if not settings.ENABLE_AUTHENTICATION:
        # Return a default user when authentication is disabled
        return {
            "user_id": "default_user",
            "email": "default@example.com",
            "scopes": ["read", "write"],
            "authenticated": False,
        }

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required")

    try:
        user_data = await auth_manager.verify_token(token)
        return user_data
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")


def _get_cache_key(query_text: str, metadata_filters: Dict[str, Any], tags: List[str], path_query: str) -> str:
    """Generate cache key for RAG queries."""
    import hashlib
    import json

    cache_data = {
        "query": query_text.lower().strip(),
        "filters": metadata_filters,
        "tags": sorted(tags) if tags else [],
        "path": path_query or "",
    }
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_str.encode()).hexdigest()


def _get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached RAG result if valid."""
    if not settings.RAG_CACHE_ENABLED:
        return None
    return _rag_cache.get(cache_key)


def _cache_result(cache_key: str, result: Dict[str, Any]):
    """Cache RAG result with enhanced LRU cache."""
    if not settings.RAG_CACHE_ENABLED:
        return
    _rag_cache.put(cache_key, result)


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
    Perform semantic search on vectorized documents
    """
    if not qdrant_store:
        raise HTTPException(status_code=503, detail="Qdrant service unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to query documents")

    try:
        # Log rate limiting information
        rate_limit_key = get_user_id_for_rate_limiting(request)
        logger.info(f"Query request from rate limit key: {rate_limit_key}")
        logger.info(
            f"Processing semantic query: {query_data.query_text[:50]}... by user: {current_user.get('user_id', 'anonymous')}"
        )

        # Use QdrantStore to perform semantic search
        search_results = await qdrant_store.semantic_search(
            query_text=query_data.query_text,
            limit=query_data.limit,
            tag=query_data.tag,
            score_threshold=query_data.score_threshold,
        )

        return QueryVectorsResponse(
            status="success",
            query_text=query_data.query_text,
            results=search_results.get("results", []),
            total_found=len(search_results.get("results", [])),
            message=f"Found {len(search_results.get('results', []))} results for semantic query",
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


@app.post("/batch_save", response_model=BatchSaveResponse)
@limiter.limit("5/minute")  # Lower limit for batch operations
@api_retry()
async def batch_save_documents(
    request: Request,
    batch_data: BatchSaveRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Save multiple documents in a single batch operation
    """
    if not qdrant_store or not vectorization_tool:
        raise HTTPException(status_code=503, detail="Vector services unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "write"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to save documents")

    batch_id = batch_data.batch_id or f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    results = []
    successful_saves = 0
    failed_saves = 0

    logger.info(f"Processing batch save with {len(batch_data.documents)} documents, batch_id: {batch_id}")

    try:
        for doc_request in batch_data.documents:
            try:
                # Enhanced metadata for batch processing
                enhanced_metadata = {
                    **doc_request.metadata,
                    "api_source": "a2a_gateway_batch",
                    "batch_id": batch_id,
                    "received_at": datetime.utcnow().isoformat(),
                    "content_length": len(doc_request.content),
                    "user_id": current_user.get("user_id"),
                    "user_email": current_user.get("email"),
                }

                # Use vectorization tool with timeout and enhanced error handling
                try:
                    result = await asyncio.wait_for(
                        vectorization_tool.vectorize_document(
                            doc_id=doc_request.doc_id,
                            content=doc_request.content,
                            metadata=enhanced_metadata,
                            tag=doc_request.tag,
                            update_firestore=doc_request.update_firestore,
                        ),
                        timeout=30.0,  # 30 second timeout per document
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Document processing timed out for {doc_request.doc_id}")

                if result.get("status") == "success":
                    successful_saves += 1
                    response = SaveDocumentResponse(
                        status="success",
                        doc_id=doc_request.doc_id,
                        message=f"Document {doc_request.doc_id} saved successfully in batch",
                        vector_id=result.get("vector_id"),
                        embedding_dimension=result.get("embedding_dimension"),
                        firestore_updated=doc_request.update_firestore,
                    )
                else:
                    failed_saves += 1
                    error_msg = result.get("error", "Unknown error")

                    # Categorize errors for better handling
                    if "rate limit" in error_msg.lower() or "quota" in error_msg.lower():
                        raise RateLimitError(f"Rate limit exceeded for {doc_request.doc_id}: {error_msg}")
                    elif "validation" in error_msg.lower() or "invalid" in error_msg.lower():
                        raise ValidationError(f"Validation error for {doc_request.doc_id}: {error_msg}")
                    else:
                        raise ServerError(f"Server error for {doc_request.doc_id}: {error_msg}")

                results.append(response)

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.1)

            except (RateLimitError, ValidationError, ServerError, TimeoutError) as e:
                failed_saves += 1
                logger.error(f"Categorized error processing document {doc_request.doc_id} in batch: {e}")
                results.append(
                    SaveDocumentResponse(
                        status="error",
                        doc_id=doc_request.doc_id,
                        message=f"Error processing document {doc_request.doc_id}: {type(e).__name__}",
                        error=str(e),
                    )
                )
            except Exception as e:
                failed_saves += 1
                logger.error(f"Unexpected error processing document {doc_request.doc_id} in batch: {e}")
                results.append(
                    SaveDocumentResponse(
                        status="error",
                        doc_id=doc_request.doc_id,
                        message=f"Internal error processing document {doc_request.doc_id}",
                        error=str(e),
                    )
                )

        return BatchSaveResponse(
            status="completed",
            batch_id=batch_id,
            total_documents=len(batch_data.documents),
            successful_saves=successful_saves,
            failed_saves=failed_saves,
            results=results,
            message=f"Batch save completed: {successful_saves} successful, {failed_saves} failed",
        )

    except Exception as e:
        logger.error(f"Error in batch save operation: {e}")
        return BatchSaveResponse(
            status="error",
            batch_id=batch_id,
            total_documents=len(batch_data.documents),
            successful_saves=successful_saves,
            failed_saves=failed_saves,
            results=results,
            message="Internal error during batch save operation",
            error=str(e),
        )


@app.post("/batch_query", response_model=BatchQueryResponse)
@limiter.limit("10/minute")  # Higher limit for batch queries
@api_retry()
async def batch_query_vectors(
    request: Request,
    batch_data: BatchQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Execute multiple semantic queries in a single batch operation
    """
    if not qdrant_store:
        raise HTTPException(status_code=503, detail="Qdrant service unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to query documents")

    batch_id = batch_data.batch_id or f"query_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    results = []
    successful_queries = 0
    failed_queries = 0

    logger.info(f"Processing batch query with {len(batch_data.queries)} queries, batch_id: {batch_id}")

    try:
        for query_request in batch_data.queries:
            try:
                # Use QdrantStore to perform semantic search with timeout and enhanced error handling
                try:
                    search_results = await asyncio.wait_for(
                        qdrant_store.semantic_search(
                            query_text=query_request.query_text,
                            limit=query_request.limit,
                            tag=query_request.tag,
                            score_threshold=query_request.score_threshold,
                        ),
                        timeout=15.0,  # 15 second timeout per query
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Query processing timed out for '{query_request.query_text[:50]}...'")

                successful_queries += 1
                response = QueryVectorsResponse(
                    status="success",
                    query_text=query_request.query_text,
                    results=search_results.get("results", []),
                    total_found=len(search_results.get("results", [])),
                    message=f"Found {len(search_results.get('results', []))} results for query in batch",
                )

                results.append(response)

                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.05)

            except (RateLimitError, ValidationError, ServerError, TimeoutError) as e:
                failed_queries += 1
                logger.error(f"Categorized error processing query '{query_request.query_text[:50]}...' in batch: {e}")
                results.append(
                    QueryVectorsResponse(
                        status="error",
                        query_text=query_request.query_text,
                        results=[],
                        total_found=0,
                        message=f"Error during query processing: {type(e).__name__}",
                        error=str(e),
                    )
                )
            except Exception as e:
                failed_queries += 1
                logger.error(f"Unexpected error processing query '{query_request.query_text[:50]}...' in batch: {e}")
                results.append(
                    QueryVectorsResponse(
                        status="error",
                        query_text=query_request.query_text,
                        results=[],
                        total_found=0,
                        message="Internal error during query processing",
                        error=str(e),
                    )
                )

        return BatchQueryResponse(
            status="completed",
            batch_id=batch_id,
            total_queries=len(batch_data.queries),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            results=results,
            message=f"Batch query completed: {successful_queries} successful, {failed_queries} failed",
        )

    except Exception as e:
        logger.error(f"Error in batch query operation: {e}")
        return BatchQueryResponse(
            status="error",
            batch_id=batch_id,
            total_queries=len(batch_data.queries),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            results=results,
            message="Internal error during batch query operation",
            error=str(e),
        )


@app.post("/cskh_query", response_model=CSKHQueryResponse)
@limiter.limit("15/minute")  # Moderate rate limit for customer care queries
@api_retry()
async def cskh_query(
    request: Request,
    query_data: CSKHQueryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    CSKH (Customer Care) Agent endpoint for contextual knowledge base queries.
    Optimized RAG search with caching, metadata filtering, and customer context.
    """
    start_time = time.time()

    if not qdrant_store or not vectorization_tool:
        raise HTTPException(status_code=503, detail="Vector search services unavailable")

    # Check user permissions
    if settings.ENABLE_AUTHENTICATION and not auth_manager.validate_user_access(current_user, "read"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for CSKH queries")

    logger.info(f"CSKH query from user {current_user.get('user_id', 'unknown')}: '{query_data.query_text[:100]}...'")

    try:
        # Generate cache key for optimization
        cache_key = _get_cache_key(
            query_data.query_text, query_data.metadata_filters or {}, query_data.tags or [], query_data.path_query or ""
        )

        # Check cache first
        cached_result = _get_cached_result(cache_key)
        if cached_result:
            response_time = (time.time() - start_time) * 1000
            logger.info(f"CSKH query cache hit for user {current_user.get('user_id')}")

            # Record cache hit metrics
            cache_duration = time.time() - start_time
            record_cskh_query("success", cache_duration)
            record_rag_search("cskh", cache_duration, cached_result["total_found"], cached=True)
            record_a2a_api_request("cskh_query", "success", cache_duration)

            return CSKHQueryResponse(
                status="success",
                query_text=query_data.query_text,
                customer_context=query_data.customer_context or {},
                results=cached_result["results"],
                total_found=cached_result["total_found"],
                rag_info=cached_result["rag_info"],
                response_time_ms=response_time,
                cached=True,
                message=f"Found {cached_result['total_found']} cached results for CSKH query",
            )

        # Perform RAG search with metrics
        with MetricsTimer("cskh_rag_search"):
            rag_result = await asyncio.wait_for(
                qdrant_rag_search(
                    query_text=query_data.query_text,
                    metadata_filters=query_data.metadata_filters,
                    tags=query_data.tags,
                    path_query=query_data.path_query,
                    limit=query_data.limit,
                    score_threshold=query_data.score_threshold,
                ),
                timeout=10.0,  # 10 second timeout for CSKH queries
            )

        # Record metrics
        record_semantic_search()
        search_duration = time.time() - start_time

        if rag_result["status"] == "success":
            # Enrich results with customer context if requested
            enriched_results = rag_result["results"]
            if query_data.include_context and query_data.customer_context:
                for result in enriched_results:
                    result["customer_context"] = query_data.customer_context

            # Cache successful results
            cache_data = {
                "results": enriched_results,
                "total_found": rag_result["count"],
                "rag_info": rag_result.get("rag_info", {}),
            }
            _cache_result(cache_key, cache_data)

            response_time = (time.time() - start_time) * 1000

            # Record successful CSKH query metrics
            record_cskh_query("success", search_duration)
            record_rag_search("cskh", search_duration, rag_result["count"], cached=False)
            record_a2a_api_request("cskh_query", "success", search_duration)

            return CSKHQueryResponse(
                status="success",
                query_text=query_data.query_text,
                customer_context=query_data.customer_context or {},
                results=enriched_results,
                total_found=rag_result["count"],
                rag_info=rag_result.get("rag_info", {}),
                response_time_ms=response_time,
                cached=False,
                message=f"Found {rag_result['count']} results for CSKH query",
            )
        else:
            # Handle RAG search failure
            response_time = (time.time() - start_time) * 1000

            # Record failed CSKH query metrics
            record_cskh_query("error", search_duration)
            record_a2a_api_request("cskh_query", "error", search_duration)
            record_a2a_api_error("cskh_query", "rag_failure")

            return CSKHQueryResponse(
                status="error",
                query_text=query_data.query_text,
                customer_context=query_data.customer_context or {},
                results=[],
                total_found=0,
                rag_info={},
                response_time_ms=response_time,
                cached=False,
                message="RAG search failed",
                error=rag_result.get("error", "Unknown RAG error"),
            )

    except asyncio.TimeoutError:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"CSKH query timeout for user {current_user.get('user_id')}")

        # Record timeout metrics
        record_cskh_query("timeout", time.time() - start_time)
        record_a2a_api_request("cskh_query", "error", time.time() - start_time)
        record_a2a_api_error("cskh_query", "timeout")

        return CSKHQueryResponse(
            status="error",
            query_text=query_data.query_text,
            customer_context=query_data.customer_context or {},
            results=[],
            total_found=0,
            rag_info={},
            response_time_ms=response_time,
            cached=False,
            message="Query processing timed out",
            error="Request timeout after 10 seconds",
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"CSKH query error for user {current_user.get('user_id')}: {e}")

        # Record error metrics
        record_cskh_query("error", time.time() - start_time)
        record_a2a_api_request("cskh_query", "error", time.time() - start_time)
        record_a2a_api_error("cskh_query", "server_error")

        return CSKHQueryResponse(
            status="error",
            query_text=query_data.query_text,
            customer_context=query_data.customer_context or {},
            results=[],
            total_found=0,
            rag_info={},
            response_time_ms=response_time,
            cached=False,
            message="Internal error during CSKH query processing",
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
            "api": {
                "save": "/save",
                "query": "/query",
                "search": "/search",
                "batch_save": "/batch_save",
                "batch_query": "/batch_query",
                "cskh_query": "/cskh_query",
            },
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
