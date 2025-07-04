import pytest
import os

def pytest_addoption(parser):
    """Add command line options for pytest."""
    parser.addoption(
        "--qdrant-mock", 
        action="store_true",
        help="Use mocked Qdrant services (default: True)"
    )

def pytest_configure(config):
    """Configure pytest with environment variables."""
    # Ensure mock environment is set by default
    if not os.environ.get("QDRANT_MOCK"):
        os.environ["QDRANT_MOCK"] = "1"
    if not os.environ.get("FIRESTORE_MOCK"):
        os.environ["FIRESTORE_MOCK"] = "1"
    if not os.environ.get("DISABLE_REAL_SERVICES"):
        os.environ["DISABLE_REAL_SERVICES"] = "1"
