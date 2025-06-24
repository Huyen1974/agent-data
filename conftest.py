import pytest
import pathlib
import sys
import os

def pytest_collection_modifyitems(session, config, items):
    """Filter collected items to match manifest_519.txt exactly - g2y-fix-fixtures-4 FINAL."""
    
    print(f">>> HOOK CALLED! Original count: {len(items)}", file=sys.stderr, flush=True)
    
    # Find manifest file using multiple paths  
    manifest_file = None
    potential_paths = [
        pathlib.Path("/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/tests/manifest_519.txt"),
        pathlib.Path(__file__).parent / "tests" / "manifest_519.txt",
        pathlib.Path(__file__).parent.parent / "tests" / "manifest_519.txt",
    ]
    
    for path in potential_paths:
        if path.exists():
            manifest_file = path
            break
    
    if not manifest_file:
        print(f">>> ERROR: manifest_519.txt not found in any location", file=sys.stderr)
        pytest.exit("manifest_519.txt not found - cannot enforce test collection", 1)
    
    print(f">>> Loading manifest from: {manifest_file}", file=sys.stderr)
    
    # Load manifest nodeids into set for O(1) lookup 
    manifest_nodeids = set()
    try:
        with open(manifest_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    manifest_nodeids.add(line)
    except Exception as e:
        print(f">>> ERROR reading manifest: {e}", file=sys.stderr)
        pytest.exit(f"Failed to read manifest_519.txt: {e}", 1)
    
    print(f">>> Loaded {len(manifest_nodeids)} nodeids from manifest", file=sys.stderr)
    
    if len(manifest_nodeids) != 519:
        pytest.exit(f"Manifest contains {len(manifest_nodeids)} tests, expected 519", 1)
    
    # Filter items to only those in manifest - exact nodeid matching
    original_count = len(items)
    filtered_items = []
    
    for item in items:
        nodeid = str(item.nodeid)
        if nodeid in manifest_nodeids:
            filtered_items.append(item)
    
    # Replace items list in-place
    items[:] = filtered_items
    final_count = len(items)
    
    print(f">>> Collection filter: {original_count} -> {final_count} tests", file=sys.stderr)
    
    # ENFORCE exactly 519 tests - exit if not met
    if final_count != 519:
        print(f">>> FATAL: Expected exactly 519 tests, got {final_count}", file=sys.stderr)
        
        # Show diagnostic info
        collected_nodeids = {str(item.nodeid) for item in filtered_items}
        missing_from_collection = manifest_nodeids - collected_nodeids
        extra_in_collection = collected_nodeids - manifest_nodeids
        
        if missing_from_collection:
            print(f">>> Missing {len(missing_from_collection)} tests from collection (first 10):", file=sys.stderr)
            for nodeid in sorted(missing_from_collection)[:10]:
                print(f">>>   - {nodeid}", file=sys.stderr)
        
        if extra_in_collection:
            print(f">>> Extra {len(extra_in_collection)} tests in collection:", file=sys.stderr)
            for nodeid in sorted(extra_in_collection)[:10]:
                print(f">>>   + {nodeid}", file=sys.stderr)
                
        pytest.exit(f"Test collection failed: {final_count} != 519", 1)
    
    print(f">>> ✅ SUCCESS: Exactly 519 tests collected!", file=sys.stderr)


# Fixtures for test compatibility
from typing import List
from qdrant_client.http.models import PointStruct

STANDARD_SAMPLE_POINTS_RAW = [
    (9001, [0.1, 0.2, 0.8], {"original_text": "modern astronomy discoveries", "tag": "science"}),
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

# Import fixtures from dedicated file if available
try:
    from tests.fixtures_conftest import *
except ImportError:
    # Fallback fixtures
    @pytest.fixture(scope="function")
    def client():
        from fastapi.testclient import TestClient
        from api_vector_search import app
        with TestClient(app) as client:
            yield client
