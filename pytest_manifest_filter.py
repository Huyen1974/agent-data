"""Pytest plugin to filter tests based on manifest_519.txt"""
import pytest
import pathlib
import sys


def pytest_collection_modifyitems(session, config, items):
    """Filter collected items to match manifest_519.txt exactly."""
    
    print(f">>> PLUGIN HOOK CALLED! Original count: {len(items)}", file=sys.stderr, flush=True)
    
    # Find manifest file
    manifest_file = pathlib.Path("/Users/nmhuyen/Documents/Manual Deploy/mpc_back_end_for_agents/tests/manifest_519.txt")
    
    if not manifest_file.exists():
        print(f">>> ERROR: manifest_519.txt not found at {manifest_file}", file=sys.stderr)
        pytest.exit("manifest_519.txt not found - cannot enforce test collection", 1)
    
    print(f">>> Loading manifest from: {manifest_file}", file=sys.stderr)
    
    # Load manifest nodeids
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
    
    # Filter items
    original_count = len(items)
    filtered_items = []
    
    for item in items:
        nodeid = str(item.nodeid)
        if nodeid in manifest_nodeids:
            filtered_items.append(item)
    
    # Replace items
    items[:] = filtered_items
    final_count = len(items)
    
    print(f">>> Collection filter: {original_count} -> {final_count} tests", file=sys.stderr)
    
    # ENFORCE exactly 519 tests
    if final_count != 519:
        print(f">>> FATAL: Expected exactly 519 tests, got {final_count}", file=sys.stderr)
        
        # Show diagnostics
        collected_nodeids = {str(item.nodeid) for item in filtered_items}
        missing = manifest_nodeids - collected_nodeids
        if missing:
            print(f">>> Missing {len(missing)} tests (first 10):", file=sys.stderr)
            for nodeid in sorted(missing)[:10]:
                print(f">>>   - {nodeid}", file=sys.stderr)
                
        pytest.exit(f"Test collection failed: {final_count} != 519", 1)
    
    print(f">>> ✅ SUCCESS: Exactly 519 tests collected!", file=sys.stderr) 