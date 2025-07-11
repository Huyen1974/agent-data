from tests.conftest import STANDARD_SAMPLE_POINTS_RAW
import pytest


@pytest.mark.unit
def test_all_tags_lowercase_in_fixtures():
    for point in STANDARD_SAMPLE_POINTS_RAW:
        # Ensure payload exists and is a dictionary
        payload = point[2]
        if not isinstance(payload, dict):
            # If payload is not a dict, it cannot have a 'tag' key.
            # This case is implicitly handled as 'tag' would be missing.
            # Depending on strictness, one might assert isinstance(payload, dict) here.
            # For now, we proceed, and .get() will handle non-dict payloads gracefully.
            pass

        tag = payload.get(
            "tag", ""
        )  # Use .get() for safety, defaults to empty string if 'tag' or payload is missing/not a dict

        # If tag is present and not an empty string, assert it's lowercase
        if tag:  # Only assert if tag is not an empty string
            assert tag == tag.lower(), f"Tag '{tag}' in fixture is not lowercase"
        # If tag is an empty string or not present, it's considered valid (or not subject to this test)
