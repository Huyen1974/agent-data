# -*- coding: utf-8 -*-
import pathlib, pytest

ROOT = pathlib.Path(__file__).parent
MANIFEST = {l.strip() for l in (ROOT / "tests" / "manifest_LOCK.txt").read_text().splitlines() if l.strip()}

def pytest_collection_modifyitems(session, config, items):
    items[:] = [i for i in items if i.nodeid in MANIFEST]
    assert len(items) == 519, f"Expected 519, got {len(items)}"

# expose legacy fixtures so tests keep working
try:
    from tests.fixtures_conftest import *   # noqa: F403,F401
except ImportError:
    pass
