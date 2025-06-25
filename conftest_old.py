import pytest
import pathlib
import sys
import os

# Module-level debug output to confirm loading
print(">>> CONFTEST.PY MODULE LOADED!", file=sys.stderr, flush=True)
print(">>> CONFTEST.PY LOADED!", file=sys.stderr, flush=True)

def pytest_collection_modifyitems(session, config, items):
    """Filter collected items to match manifest_106.txt exactly - enforce exactly 106 tests."""
    
    print(f">>> HOOK CALLED! Original count: {len(items)}", file=sys.stderr, flush=True)
    
    # Find manifest file using hard-coded relative path
    manifest_file = pathlib.Path(__file__).parent / "tests" / "manifest_106.txt"
    
    if not manifest_file.exists():
        print(f">>> ERROR: manifest_106.txt not found at {manifest_file}", file=sys.stderr)
        pytest.exit("manifest_106.txt not found - cannot enforce test collection", 1)
    
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
        pytest.exit(f"Failed to read manifest_106.txt: {e}", 1)
    
    print(f">>> Loaded {len(manifest_nodeids)} nodeids from manifest", file=sys.stderr)
    
    # Enforce exactly 106 tests in manifest
    if len(manifest_nodeids) != 106:
        print(f">>> ERROR: Manifest contains {len(manifest_nodeids)} tests, expected exactly 106", file=sys.stderr)
        pytest.exit(f"Manifest contains {len(manifest_nodeids)} tests, expected exactly 106", 1)
    
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
    
    # Enforce exactly 106 tests collected
    if final_count != 106:
        print(f">>> ERROR: Expected exactly 106 tests, got {final_count}", file=sys.stderr)
        pytest.exit(f"Test collection failed: expected 106 tests, got {final_count}", 1)
    
    print(f">>> ✅ SUCCESS: {final_count} tests collected and filtered!", file=sys.stderr) 