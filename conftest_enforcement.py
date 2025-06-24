import pathlib, pytest
MANIFEST_PATH = pathlib.Path(__file__).parent / "tests" / "manifest_519.txt"
WHITELIST = {l.strip() for l in MANIFEST_PATH.read_text().splitlines() if l.strip()}

def pytest_collection_modifyitems(session, config, items):
    items[:] = [i for i in items if i.nodeid in WHITELIST]
    assert len(items) == 519, f"Expected 519 selected, got {len(items)}" 