import sys
import os
import pytest
from fastapi.testclient import TestClient
from qdrant_client.http.models import PointStruct, Distance, VectorParams
import api_vector_search  # Main application
from api_vector_search import app, get_qdrant_store  # App and dependency getter
from typing import List, Generator

# Import the mocks from the dedicated file
from tests.mocks.qdrant_basic import (
    FakeQdrantClient,
    mock_embedding_function_for_conftest as mock_embedding_function,
)

# Placeholder for actual QdrantStore, assuming it's in agent_data.vector_store.qdrant_store
# This is needed for type hinting and potentially for resetting singleton instance
try:
    from agent_data.vector_store.qdrant_store import QdrantStore
except ImportError:
    QdrantStore = None  # Fallback if not found, tests might fail if QdrantStore is essential

# Standard sample points for seeding the mock Qdrant
# These should align with what tests expect, using 1536-dim vectors.
# Tags will be lowercased by the FakeQdrantClient's upsert method.
STANDARD_SAMPLE_POINTS_RAW = [
    # id, short_vector_prefix (3-dim), payload
    (
        9001,
        [0.1, 0.2, 0.8],
        {"original_text": "modern astronomy discoveries", "tag": "science"},
    ),  # Tag will be lowercased
    (9002, [0.8, 0.1, 0.1], {"original_text": "new chicken recipe", "tag": "cooking"}),
    (9003, [0.2, 0.8, 0.1], {"original_text": "ancient rome history", "tag": "history"}),
    (1001, [0.1, 0.2, 0.7], {"original_text": "Deep space exploration", "tag": "science"}),
    (1002, [0.1, 0.2, 0.6], {"original_text": "Hubble telescope images", "tag": "science"}),
    (1003, [0.1, 0.2, 0.5], {"original_text": "Black hole theories", "tag": "science"}),
    (1004, [0.5, 0.5, 0.5], {"original_text": "Unrelated topic", "tag": "other"}),
    (2001, [0.01, 0.005, 0.0], {"original_text": "Item 1 Page", "tag": "pages"}),
    (2002, [0.02, 0.01, 0.0], {"original_text": "Item 2 Page", "tag": "pages"}),
    (2003, [0.03, 0.015, 0.0], {"original_text": "Item 3 Page", "tag": "pages"}),
    (2004, [0.04, 0.02, 0.0], {"original_text": "Item 4 Page", "tag": "pages"}),
    (2005, [0.05, 0.025, 0.0], {"original_text": "Item 5 Page", "tag": "pages"}),
    (2006, [0.06, 0.03, 0.0], {"original_text": "Item 6 Page", "tag": "pages"}),
]


def get_standard_points_for_mock() -> List[PointStruct]:
    points = []
    for p_id, short_vector, p_payload in STANDARD_SAMPLE_POINTS_RAW:
        full_vector = [0.0] * 1536  # Pad to 1536 dimensions
        for i, val in enumerate(short_vector):
            if i < 1536:
                full_vector[i] = val
        points.append(PointStruct(id=p_id, vector=full_vector, payload=p_payload))
    return points


@pytest.fixture(scope="function")
def client_with_qdrant_override(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    """
    Pytest fixture to provide a FastAPI TestClient with a mocked Qdrant backend.

    - Sets necessary environment variables for the QdrantStore.
    - Clears any existing data in the FakeQdrantClient.
    - Patches the QdrantClient used by QdrantStore to be an instance of FakeQdrantClient.
    - Patches the OpenAI embedding function.
    - Seeds the FakeQdrantClient with standard sample data.
    - Resets QdrantStore singleton instance to ensure it uses mocks.
    - Overrides FastAPI's get_qdrant_store dependency.
    - Yields a TestClient for making API requests.
    - Cleans up overrides after the test.
    """

    # 1. Set environment variables for test scope
    monkeypatch.setenv("QDRANT_URL", "http://mock-qdrant:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "mock-key")
    monkeypatch.setenv("QDRANT_COLLECTION_NAME", "test_collection")  # Standardized collection name for tests
    monkeypatch.setenv("ENABLE_FIRESTORE_SYNC", "false")  # Disable Firestore for tests

    # 2. Clear FakeQdrantClient data & Instantiate
    # Assuming FakeQdrantClient from tests.mocks.qdrant_basic has a class method 'clear_all_data'
    # and its constructor is compatible with QdrantClient(url=..., api_key=...)
    if hasattr(FakeQdrantClient, "clear_all_data") and callable(FakeQdrantClient.clear_all_data):
        FakeQdrantClient.clear_all_data()

    # This instance will be used by the QdrantStore
    # Its constructor must match how QdrantStore instantiates the real QdrantClient
    # i.e., FakeQdrantClient(url=..., api_key=...)
    # This requires tests/mocks/qdrant_basic.py::FakeQdrantClient to be updated.
    mock_qdrant_url = os.getenv("QDRANT_URL")
    mock_qdrant_api_key = os.getenv("QDRANT_API_KEY")

    # Critical Assumption: FakeQdrantClient in qdrant_basic.py will be refactored to have a
    # constructor like: __init__(self, url, api_key=None, **kwargs)
    # and synchronous methods.
    fake_qdrant_client_instance = FakeQdrantClient(url=mock_qdrant_url, api_key=mock_qdrant_api_key)

    # 3. Patch the QdrantClient where QdrantStore imports it from
    def mock_qdrant_client_constructor(*args, **kwargs):
        # This function will be called when QdrantStore attempts to create a QdrantClient.
        # We return our pre-configured FakeQdrantClient instance.
        # Args passed by QdrantStore (like url, api_key) are already used to init fake_qdrant_client_instance.
        return fake_qdrant_client_instance

    # Patch the client at the source where QdrantStore is expected to import it
    # This path needs to be correct for where QdrantStore looks for QdrantClient
    qdrant_client_path = "agent_data.vector_store.qdrant_store.QdrantClient"
    try:
        # Attempt to import the module to ensure it exists before patching
        # This also helps confirm the path is valid.
        module_path, class_name = qdrant_client_path.rsplit(".", 1)
        __import__(module_path)
        monkeypatch.setattr(qdrant_client_path, mock_qdrant_client_constructor)
    except (ImportError, AttributeError) as e:
        # Fallback if the primary path is not found, try common 'qdrant_client.QdrantClient'
        # This is less ideal as it might not be where QdrantStore gets it from.
        # print(f"Warning: Could not patch QdrantClient at '{qdrant_client_path}'. Error: {e}. Trying 'qdrant_client.QdrantClient'.")
        try:
            monkeypatch.setattr("qdrant_client.QdrantClient", mock_qdrant_client_constructor)
        except (ImportError, AttributeError) as e_fallback:
            raise RuntimeError(
                f"Failed to patch QdrantClient at both '{qdrant_client_path}' and 'qdrant_client.QdrantClient'. "
                f"Ensure QdrantStore imports QdrantClient from a patchable location. Errors: {e}, {e_fallback}"
            )

    # 4. Reset QdrantStore singleton instance (if applicable)
    if QdrantStore and hasattr(QdrantStore, "_instance"):  # Reset if it's a singleton
        QdrantStore._instance = None
    if QdrantStore and hasattr(QdrantStore, "_initialized"):  # Reset init flag
        QdrantStore._initialized = False
    # If _initialized is on the instance itself (after _instance was reset and it re-instantiates)
    if (
        QdrantStore
        and hasattr(QdrantStore, "_instance")
        and getattr(QdrantStore, "_instance", None) is not None
        and hasattr(QdrantStore._instance, "_initialized")
    ):
        QdrantStore._instance._initialized = False

    # 5. Seed data into the FakeQdrantClient
    collection_name = os.getenv("QDRANT_COLLECTION_NAME")  # Should be "test_collection"

    # Ensure collection exists. FakeQdrantClient methods (create_collection, upsert_points)
    # are assumed to be synchronous after refactor of qdrant_basic.py.
    if not fake_qdrant_client_instance.collection_exists(collection_name=collection_name):
        fake_qdrant_client_instance.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    sample_points = get_standard_points_for_mock()
    if sample_points:
        # Assuming FakeQdrantClient has a synchronous 'upsert_points' or 'upsert' method.
        # The one in qdrant_basic.py is 'upsert_points' (needs to be sync).
        fake_qdrant_client_instance.upsert_points(collection_name=collection_name, points=sample_points)

    # 6. Patch _generate_openai_embedding for the application
    # mock_embedding_function from qdrant_basic.py is async, matching api_vector_search._generate_openai_embedding
    monkeypatch.setattr("api_vector_search._generate_openai_embedding", mock_embedding_function)

    # 7. Override FastAPI dependency for get_qdrant_store
    def override_get_qdrant_store():
        # Returns a QdrantStore instance. Due to patching and singleton reset (if applicable),
        # this QdrantStore should be initialized with the FakeQdrantClient.
        if QdrantStore:
            # If QdrantStore is a singleton, get_instance() or QdrantStore() should provide the
            # correctly initialized (mocked) instance.
            return QdrantStore()  # Relies on QdrantStore's constructor picking up env vars and patched client
        return None  # Should not happen if QdrantStore is integral

    if QdrantStore:  # Only override if QdrantStore was successfully imported
        app.dependency_overrides[get_qdrant_store] = override_get_qdrant_store

    # Ensure project root is in sys.path for imports like 'agent_data'
    _PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _PROJECT_ROOT not in sys.path:
        # Use monkeypatch to temporarily add to sys.path if needed, though this is often a sign of project structure issues.
        # For conftest, modifying sys.path directly is common but has broader effects.
        # Let's keep it simple as it was in the original conftest.
        sys.path.insert(0, _PROJECT_ROOT)

    # 8. Yield TestClient
    with TestClient(app) as client:
        yield client

    # 9. Cleanup
    if QdrantStore:  # Clear overrides if they were set
        app.dependency_overrides.clear()

    # monkeypatch automatically undoes its changes (setenv, setattr)
    # If sys.path was modified, it remains modified for the rest of the test session.
    # This is usually acceptable for test environments.
    # If FakeQdrantClient needs explicit teardown, it should be done here or via a finalizer.
    # For now, clear_all_data() at the start of the next test using this fixture handles state.


# If there are any session-level teardown requirements (e.g. for FakeQdrantClient if it holds resources),
# they could be managed with a session-scoped fixture with a finalizer, but the prompt focuses on per-test clearance.

# --- 2. Early Global Patching & Environment Variable Setup ---
# Add the project root to the Python path *before* other project imports
# Ensures 'agent_data' can be imported.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Store original environment variables
_ORIGINAL_ENV_VARS = {
    "QDRANT_URL": os.environ.get("QDRANT_URL"),
    "QDRANT_API_KEY": os.environ.get("QDRANT_API_KEY"),
    "QDRANT_COLLECTION_NAME": os.environ.get("QDRANT_COLLECTION_NAME"),
    "ENABLE_FIRESTORE_SYNC": os.environ.get("ENABLE_FIRESTORE_SYNC"),
}

# Set dummy environment variables for all tests
os.environ["QDRANT_URL"] = "http://dummy:6333"  # Dummy URL, won't be hit
os.environ["QDRANT_API_KEY"] = "dummy-key"  # Dummy key
os.environ["QDRANT_COLLECTION_NAME"] = "my_collection"  # Consistent collection name
os.environ["ENABLE_FIRESTORE_SYNC"] = "false"  # Disable Firestore for tests

# Perform the global patch of QdrantClient
_ORIGINAL_QDRANT_CLIENT = None
try:
    # Import the module where QdrantClient is defined or imported by QdrantStore
    import agent_data.vector_store.qdrant_store

    # Store the original client
    _ORIGINAL_QDRANT_CLIENT = agent_data.vector_store.qdrant_store.QdrantClient
    # Perform the patch by direct assignment
    agent_data.vector_store.qdrant_store.QdrantClient = FakeQdrantClient
except ImportError as e:
    print(
        f"CRITICAL WARNING: Could not import 'agent_data.vector_store.qdrant_store' for patching QdrantClient. Tests will likely fail. Error: {e}",
        file=sys.stderr,
    )
except AttributeError as e:
    print(
        f"CRITICAL WARNING: 'QdrantClient' not found in 'agent_data.vector_store.qdrant_store' for patching. Tests will likely fail. Error: {e}",
        file=sys.stderr,
    )


# --- 3. Session-Scoped Cleanup Fixture ---
def pytest_configure(config):
    """Configure pytest with environment variable mocking."""
    import os
    os.environ["OPENAI_API_KEY"] = "mock_key"
    os.environ["GCP_KEY"] = "mock_key"

@pytest.fixture(scope="session", autouse=True)
def _manage_env_and_qdrant_patch():
    # Setup part is done by global code execution above (env vars set, client patched)
    yield  # Let all tests in the session run

    # Teardown: Restore original environment variables
    for key, value in _ORIGINAL_ENV_VARS.items():
        if value is None:
            if key in os.environ:  # Only delete if it was not set originally
                del os.environ[key]
        else:
            os.environ[key] = value  # Restore original value

    # Teardown: Restore original QdrantClient
    if _ORIGINAL_QDRANT_CLIENT is not None:
        try:
            import agent_data.vector_store.qdrant_store  # Re-import just in case

            agent_data.vector_store.qdrant_store.QdrantClient = _ORIGINAL_QDRANT_CLIENT
        except (ImportError, AttributeError) as e:
            # If it failed to import/patch initially, or if module was manipulated unexpectedly
            print(f"Warning: Could not restore original QdrantClient. Error: {e}", file=sys.stderr)

    # Clean up shared data of FakeQdrantClient at the very end of session
    if hasattr(FakeQdrantClient, "clear_all_data") and callable(FakeQdrantClient.clear_all_data):
        FakeQdrantClient.clear_all_data()


# --- 4. CLI Option for Test Counting ---
# Removing pytest_addoption and pytest_collection_modifyitems from tests/conftest.py
# as these are now handled by the root conftest.py


# --- 5. Function-Scoped Per-Test Reset Fixture --- # Renumbering for clarity
@pytest.fixture(autouse=True)  # Default scope is "function"
def _reset_qdrant_state_before_each_test():
    # Clear the shared in-memory store of FakeQdrantClient before each test
    FakeQdrantClient.clear_all_data()

    # Attempt to reset QdrantStore singleton instance to ensure it reinitializes
    # with the patched FakeQdrantClient and uses the now-empty shared data.
    try:
        from agent_data.vector_store.qdrant_store import QdrantStore

        # Check if QdrantStore is a class that might have _instance
        if isinstance(QdrantStore, type) and hasattr(QdrantStore, "_instance"):
            QdrantStore._instance = None

        # Reset _initialized flag if it exists (handle both class and instance attribute)
        if isinstance(QdrantStore, type) and hasattr(QdrantStore, "_initialized"):
            QdrantStore._initialized = False
        elif (
            hasattr(QdrantStore, "_instance")
            and QdrantStore._instance is not None
            and hasattr(QdrantStore._instance, "_initialized")
        ):
            # If _initialized is on the instance itself
            QdrantStore._instance._initialized = False

    except ImportError:
        # QdrantStore module might not be imported by all tests, or at all if patching failed.
        pass
    except AttributeError:
        # QdrantStore might not have _instance or _initialized (e.g., if its structure changed)
        pass

    # Re-set environment variables for safety, as they might be cleared by other tests
    # or test runner configurations if not using monkeypatch within this fixture too.
    # However, the session-scoped fixture _manage_env_and_qdrant_patch and global setup
    # should ideally handle this. For robustness, we ensure they are set as expected by QdrantStore.
    os.environ["QDRANT_URL"] = "http://dummy:6333"
    os.environ["QDRANT_API_KEY"] = "dummy-key"
    os.environ["QDRANT_COLLECTION_NAME"] = "my_collection"
    os.environ["ENABLE_FIRESTORE_SYNC"] = "false"

    # Critical: Reset QdrantStore singleton to ensure it re-initializes with FakeQdrantClient for this test
    if QdrantStore and hasattr(QdrantStore, "_instance"):
        QdrantStore._instance = None
    if QdrantStore and hasattr(QdrantStore, "_initialized"):
        QdrantStore._initialized = False

    # Patch _generate_openai_embedding for api_vector_search if not already globally patched or if it needs per-test patching
    # This is usually done globally or via a broader scope fixture.
    # For safety, if a test somehow unpatches it, this would re-patch.
    # However, the current setup relies on global patching and client_with_qdrant_override for specific scenarios.
    # It might be redundant here unless specific tests meddle with api_vector_search directly.
    # For now, let's assume the global patch and client_with_qdrant_override handle this.

    # Get the main FastAPI app instance
    fastapi_app = api_vector_search.app

    # Override the get_qdrant_store dependency for this specific client
    # This ensures that even if global overrides are somehow bypassed or complex,
    # this client instance gets a QdrantStore using the FakeQdrantClient.
    def override_get_qdrant_store_for_client_fixture():
        if QdrantStore:
            # This will instantiate QdrantStore, which should use the globally patched FakeQdrantClient
            # because of the code run at import time in this conftest.py
            return QdrantStore()
        return None

    if QdrantStore:
        fastapi_app.dependency_overrides[get_qdrant_store] = override_get_qdrant_store_for_client_fixture

    # Yield the TestClient
    with TestClient(fastapi_app) as test_client:
        yield test_client

    # Cleanup: Clear dependency overrides after the test
    if QdrantStore:
        fastapi_app.dependency_overrides.clear()


# Example of a client fixture that uses the FastAPI app.
# This should be defined *after* the patching mechanisms are in place.
@pytest.fixture(scope="function")
def client():
    """
    Provides a TestClient instance for FastAPI.
    Ensures the app is imported *after* QdrantClient is patched.
    """
    # Import the app here to ensure it's loaded after patches
    from api_vector_search import app as fastapi_app
    from fastapi.testclient import TestClient

    # If QdrantStore is initialized upon app creation (e.g. via dependency),
    # it should now pick up the FakeQdrantClient due to the global patch.
    # The _reset_qdrant_state_before_each_test fixture should ensure
    # that QdrantStore re-initializes if it's a singleton.

    with TestClient(fastapi_app) as test_client:
        yield test_client


# CLI 126B: Enhanced mocking fixtures for external services
@pytest.fixture
def qdrant_cloud_mock():
    """
    CLI 126B: Enhanced Qdrant Cloud mock specifically for tests that require
    realistic Qdrant Cloud responses without real API calls.
    """
    from unittest.mock import Mock

    mock_client = Mock()

    # Mock collection operations with realistic responses
    mock_collections = Mock()

    # Create collection objects with proper attributes
    collection1 = Mock()
    collection1.name = "my_collection"
    collection1.status = "green"
    collection1.vectors_count = 100

    collection2 = Mock()
    collection2.name = "test_collection"
    collection2.status = "green"
    collection2.vectors_count = 50

    mock_collections.collections = [collection1, collection2]
    mock_client.get_collections = Mock(return_value=mock_collections)

    # Mock collection info
    collection_info = Mock()
    collection_info.config = Mock(
        params=Mock(vectors=Mock(size=1536, distance="Cosine")),
        optimizer_config=Mock(memmap_threshold=None),
        hnsw_config=Mock(m=16, ef_construct=100),
    )
    collection_info.status = "green"
    collection_info.vectors_count = 100
    mock_client.get_collection = Mock(return_value=collection_info)

    # Mock vector operations
    mock_client.upsert = Mock(return_value=Mock(status="completed", operation_id=123456))

    # Mock search with realistic scores
    mock_client.search = Mock(
        return_value=[
            Mock(
                id="vec_001",
                score=0.92,
                payload={
                    "doc_id": "doc_001",
                    "tag": "science",
                    "original_text": "astronomy research",
                },
            ),
            Mock(
                id="vec_002",
                score=0.87,
                payload={
                    "doc_id": "doc_002",
                    "tag": "science",
                    "original_text": "physics experiments",
                },
            ),
        ]
    )

    return mock_client


@pytest.fixture
def openai_embedding_cache():
    """
    CLI 126B: Cached OpenAI embedding fixture to avoid repeated API calls.
    Returns deterministic embeddings based on input text.
    """
    import hashlib
    import json
    from pathlib import Path

    cache_file = Path(".cache/test_embeddings.json")
    cache = {}

    # Load existing cache
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, IOError):
            cache = {}

    def get_embedding(text: str, model: str = "text-embedding-ada-002") -> list:
        cache_key = f"{model}:{text}"

        if cache_key not in cache:
            # Generate deterministic embedding
            text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            embedding = []
            for i in range(1536):
                seed = (text_hash + i * 7) % 1000000
                # Normalize to [-1, 1] range with some variation
                value = (seed / 500000.0) - 1.0
                # Add small random component for more realistic distribution
                value += ((text_hash * (i + 1)) % 100 - 50) / 50000.0
                embedding.append(max(-1.0, min(1.0, value)))

            cache[cache_key] = embedding

            # Save cache
            cache_file.parent.mkdir(exist_ok=True)
            try:
                with open(cache_file, "w") as f:
                    json.dump(cache, f)
            except IOError:
                pass

        return cache[cache_key]

    return get_embedding


@pytest.fixture
def fast_e2e_mocks(qdrant_cloud_mock, openai_embedding_cache):
    """
    CLI 126B: Combined fixture for fast E2E testing with all external services mocked.
    Provides realistic responses without actual API calls.
    """
    from unittest.mock import Mock

    # Mock OpenAI client
    mock_openai = Mock()

    def mock_create(**kwargs):
        text = kwargs.get("input", "default text")
        model = kwargs.get("model", "text-embedding-ada-002")
        embedding = openai_embedding_cache(text, model)

        response = Mock()
        response.data = [Mock(embedding=embedding)]
        return response

    mock_openai.embeddings.create = Mock(side_effect=mock_create)

    # Mock GCS client
    mock_gcs = Mock()
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_blob.upload_from_string = Mock()
    mock_blob.download_as_text = Mock(return_value="Test content")
    mock_bucket.blob = Mock(return_value=mock_blob)
    mock_gcs.bucket = Mock(return_value=mock_bucket)

    # Mock Firestore client
    mock_firestore = Mock()
    mock_collection = Mock()
    mock_doc_ref = Mock()
    mock_doc_ref.set = Mock()
    mock_doc_ref.get = Mock()
    mock_doc_ref.update = Mock()
    mock_collection.document = Mock(return_value=mock_doc_ref)
    mock_firestore.collection = Mock(return_value=mock_collection)

    return {
        "qdrant_client": qdrant_cloud_mock,
        "openai_client": mock_openai,
        "gcs_client": mock_gcs,
        "firestore_client": mock_firestore,
        "embedding_cache": openai_embedding_cache,
    }
