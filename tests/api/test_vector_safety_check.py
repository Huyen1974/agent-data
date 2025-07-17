import random

import pytest

# import math # No longer needed if local normalize_vector is removed
from fastapi.testclient import TestClient

# Removed sys.path manipulation as not importing from agent_data directly here
# import sys
# import os
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)
# Removed import of non-existent normalize_vector
# from agent_data.utils.vector_utils import normalize_vector
from api_vector_search import app

client = TestClient(app)
VECTOR_DIMENSION = 1536


@pytest.fixture(scope="function", autouse=True)
def clear_storage_before_after_test():
    """Fixture to clear embeddings before and after each test."""
    # Assuming /clear_embeddings is the correct endpoint to clear all data for a fresh test run.
    # This was previously /embeddings/clear in some examples, but /clear_embeddings seems more current.
    response = client.post("/clear_embeddings")
    assert response.status_code == 200, "Failed to clear embeddings before test."
    yield
    response = client.post("/clear_embeddings")
    assert response.status_code == 200, "Failed to clear embeddings after test."


def create_random_vector(
    dimensions: int = VECTOR_DIMENSION, precision: int = 7
) -> list[float]:
    """Generates a random vector of a given dimension with specified precision."""
    return [round(random.uniform(-1, 1), precision) for _ in range(dimensions)]


# Test implementations will follow


@pytest.mark.unit
def test_vector_id_collision():
    """Tests that inserting a vector with an existing ID replaces the old one."""
    point_id = random.randint(100000, 200000)  # Using integer ID

    # First insert
    vector1 = create_random_vector()
    metadata1 = {"tag": "collision_test_v1", "source": "first_insert"}
    payload1 = {"point_id": point_id, "vector": vector1, "metadata": metadata1}

    response1 = client.post("/upsert_vector", json=payload1)
    assert response1.status_code == 200
    assert response1.json().get("status") == "ok", "First insert failed"

    # Second insert with the same ID
    vector2 = create_random_vector()
    metadata2 = {"tag": "collision_test_v2", "source": "second_insert_replaces"}
    payload2 = {"point_id": point_id, "vector": vector2, "metadata": metadata2}

    response2 = client.post("/upsert_vector", json=payload2)
    assert response2.status_code == 200
    assert response2.json().get("status") == "ok", "Second insert (overwrite) failed"

    # Retrieve the vector
    get_response = client.post("/get_vector_by_id", json={"point_id": point_id})
    assert get_response.status_code == 200
    retrieved_point = get_response.json().get("point")
    assert retrieved_point is not None

    # Confirm it matches the second vector (raw, not normalized by endpoint)
    assert retrieved_point["id"] == point_id
    # The endpoint /get_vector_by_id returns the raw vector from the store.
    assert retrieved_point["vector"] == pytest.approx(
        vector2, abs=1e-5
    )  # Compare with raw vector2
    assert retrieved_point["metadata"] == metadata2


@pytest.mark.unit
def test_vector_truncation_protection():
    """Tests that inserting a vector with incorrect (too large) dimension is rejected."""
    point_id = random.randint(200001, 300000)  # Using integer ID
    invalid_dimension = VECTOR_DIMENSION + 100  # e.g., 1536 + 100 = 1636
    vector_too_long = create_random_vector(dimensions=invalid_dimension)
    metadata = {"tag": "truncation_test", "status": "attempt_fail"}

    payload = {"point_id": point_id, "vector": vector_too_long, "metadata": metadata}

    response = client.post("/upsert_vector", json=payload)

    # Expecting a 422 Unprocessable Entity error due to Pydantic validation
    assert (
        response.status_code == 422
    ), f"API should reject oversized vector. Got {response.status_code}, {response.text}"

    error_details = response.json().get("detail")
    assert error_details is not None, "Error details missing in 422 response"

    # Check for the specific Pydantic validation error message
    # The VectorItem model has a validator for vector dimension.
    # ValueError(f"Vector must have {STANDARD_DIMENSION} dimensions, got {len(v)}")
    # FastAPI wraps this in a list of error objects.
    found_error = False
    for error in error_details:
        if isinstance(error, dict) and "msg" in error:
            # Example msg: "Value error, Vector must have 1536 dimensions, got 1636"
            # The exact message from Pydantic can start with "Value error, "
            # Or for FastAPI 0.100+ it might be more structured.
            # Let's check for the core part of the message.
            if (
                f"must have {VECTOR_DIMENSION} dimensions" in error["msg"]
                and f"got {invalid_dimension}" in error["msg"]
            ):
                found_error = True
                break
    assert found_error, f"Specific dimension error message not found in {error_details}"

    # Confirm that no vector was actually inserted with this ID (important safety check)
    get_response = client.post("/get_vector_by_id", json={"point_id": point_id})
    assert (
        get_response.status_code == 404
    ), f"Malformed vector with id {point_id} should not have been inserted."
