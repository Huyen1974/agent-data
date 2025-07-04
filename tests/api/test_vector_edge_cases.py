import random
import uuid
import sys
import os
from fastapi.testclient import TestClient

# Adjust sys.path to include the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
# The issue is that api_vector_search is a file, not a directory/package.
# We need to ensure the project root (where api_vector_search.py is) is in sys.path

# Correct path to project root from tests/api/test_vector_edge_cases.py
# tests/api/test_vector_edge_cases.py -> tests/api -> tests -> project_root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root_corrected = os.path.abspath(os.path.join(current_dir, "..", ".."))

if project_root_corrected not in sys.path:
    sys.path.insert(0, project_root_corrected)

# Now, import app from api_vector_search.py (assuming it's at the root)
from api_vector_search import app  # Assuming 'app' is defined in api_vector_search.py

client = TestClient(app)

VECTOR_DIMENSION = 1536  # Corrected to match API validation


def create_random_vector(dim=VECTOR_DIMENSION):
    return [random.random() for _ in range(dim)]


def generate_unique_tag():
    return f"test-tag-edge-{uuid.uuid4()}"


    @pytest.mark.slowdef test_get_vector_by_id_not_found():
    """
    Tests retrieving a non-existent vector by ID.
    Expected behavior: 404 Not Found.
    """
    non_existent_point_id = random.randint(9000000, 9999999)  # A high range unlikely to exist

    # Corrected: Use POST with JSON body
    response = client.post("/get_vector_by_id", json={"point_id": non_existent_point_id})

    assert (
        response.status_code == 404
    ), f"Expected status code 404 for non-existent ID, but got {response.status_code}. Response: {response.text}"

    response_json = response.json()
    assert "detail" in response_json, "Response JSON should contain a 'detail' field for errors."
    # The exact message might vary, but it should indicate not found.
    # Example: "Point id {non_existent_point_id} not found!"
    # Example from Qdrant: "Not found: Point with id {point_id} does not exist!"
    assert (
        str(non_existent_point_id) in response_json["detail"]
    ), f"Error detail should mention the point ID. Got: {response_json['detail']}"
    assert (
        "not found" in response_json["detail"].lower() or "does not exist" in response_json["detail"].lower()
    ), f"Error detail should indicate 'not found' or 'does not exist'. Got: {response_json['detail']}"


    @pytest.mark.slowdef test_upsert_vector_invalid_input():
    """
    Tests upserting a vector with invalid input (e.g., wrong vector dimension).
    Expected behavior: 422 Unprocessable Entity.
    """
    point_id = random.randint(1, 1000000)
    # Malformed vector: incorrect dimension
    malformed_vector = create_random_vector(dim=VECTOR_DIMENSION + 1)
    payload = {"tag": generate_unique_tag()}

    upsert_payload = {"points": [{"id": point_id, "vector": malformed_vector, "payload": payload}]}

    response = client.post("/upsert_vector", json=upsert_payload)

    assert (
        response.status_code == 422
    ), f"Expected status code 422 for invalid input, but got {response.status_code}. Response: {response.text}"

    response_json = response.json()
    assert "detail" in response_json, "Response JSON should contain a 'detail' field for validation errors."
    # We can check if the detail is a list (FastAPI typically returns a list of error objects)
    assert isinstance(response_json["detail"], list), "Error detail should be a list of error objects."
    assert len(response_json["detail"]) > 0, "Error detail list should not be empty."

    # Check for a message that indicates a vector dimension issue or validation error for the vector field.
    # This can be brittle if the error message changes, but provides more specific validation.
    found_vector_error = False
    for error in response_json["detail"]:
        if "loc" in error and isinstance(error["loc"], list):
            # Example loc: ["body", "points", 0, "vector"]
            if "vector" in error["loc"] or (len(error["loc"]) > 0 and "vector" in str(error["loc"][-1])):
                found_vector_error = True
                # Further check msg if needed, e.g., error["msg"] might contain "dimension"
                break
    assert (
        found_vector_error
    ), f"Validation error details did not pinpoint the 'vector' field or its dimension. Got: {response_json['detail']}"

    # Test case: Missing required field in payload (e.g. if 'tag' was mandatory by Pydantic model)
    # For now, focusing on vector dimension as requested.
    # If we wanted to test missing 'tag', we'd need to know if 'tag' is mandatory in the payload.
    # Assuming 'tag' is optional or not strictly validated at this level for this test.


    @pytest.mark.slowdef test_query_vectors_by_ids_partial_invalid():
    """
    Tests querying by a list of IDs where some are valid and some are not.
    Expected behavior: 200 OK, returns only the valid vectors.
    """
    # 1. Insert one valid vector
    valid_point_id = random.randint(2000001, 3000000)
    valid_vector = create_random_vector()
    valid_tag = generate_unique_tag()
    valid_payload_metadata = {"tag": valid_tag, "description": "valid_point"}  # Renamed for clarity, this is metadata

    # Corrected upsert payload for /upsert_vector (single item)
    # It expects point_id, vector, and metadata directly in the body.
    upsert_payload_corrected = {"point_id": valid_point_id, "vector": valid_vector, "metadata": valid_payload_metadata}

    upsert_response = client.post("/upsert_vector", json=upsert_payload_corrected)
    assert upsert_response.status_code == 200, f"Failed to upsert valid vector: {upsert_response.text}"

    # The /upsert_vector endpoint returns { "status": "success" | "updated", "point_id": id }
    # Let's check the response structure based on the API if needed, for now, status 200 is primary.
    upsert_response_json = upsert_response.json()
    assert "status" in upsert_response_json, f"Upsert response missing 'status': {upsert_response.text}"
    assert upsert_response_json["status"] == "ok", f"Upsert status not 'ok': {upsert_response_json['status']}"
    assert "point_id" in upsert_response_json, f"Upsert response missing 'point_id': {upsert_response.text}"
    assert (
        upsert_response_json["point_id"] == valid_point_id
    ), f"Upsert response point_id mismatch: {upsert_response_json['point_id']}"

    # 2. Generate a non-existent point_id
    non_existent_point_id = random.randint(9000000, 9999999)  # Unlikely to exist

    # 3. Query with 1 valid + 1 invalid point_id
    point_ids_to_query = [valid_point_id, non_existent_point_id]
    # Also test with non-existent first to ensure order doesn't matter for retrieval
    point_ids_to_query_shuffled = random.sample(point_ids_to_query, len(point_ids_to_query))

    query_body = {"point_ids": point_ids_to_query_shuffled, "limit": 10}
    query_response = client.post("/query_vectors_by_ids", json=query_body)

    # 4. Assert 200 status
    assert (
        query_response.status_code == 200
    ), f"Expected status 200 for partial invalid IDs, but got {query_response.status_code}. Response: {query_response.text}"

    # 5. Verify only the valid vector is returned
    retrieved_points = query_response.json()
    assert isinstance(retrieved_points, list), "Response should be a list of points."

    assert (
        len(retrieved_points) == 1
    ), f"Expected 1 vector to be returned, but got {len(retrieved_points)}. Queried IDs: {point_ids_to_query_shuffled}"

    returned_point = retrieved_points[0]
    assert "id" in returned_point, "Returned point missing 'id' field"
    assert "payload" in returned_point, "Returned point missing 'payload' field"
    # Vector check can be added if necessary, but often omitted due to float precision
    # assert "vector" in returned_point, "Returned point missing 'vector' field"

    assert (
        returned_point["id"] == valid_point_id
    ), f"Returned point ID {returned_point['id']} does not match valid_point_id {valid_point_id}"
    # The /query_vectors_by_ids returns points with 'payload', not 'metadata'
    # The original test had valid_payload which was the metadata.
    assert (
        returned_point["payload"] == valid_payload_metadata
    ), f"Returned point payload {returned_point['payload']} does not match valid_payload_metadata {valid_payload_metadata}"


    @pytest.mark.slowdef test_delete_vector_not_found():
    """
    Tests attempting to delete a vector that doesn't exist.
    Expected behavior: 200 OK (as Qdrant delete is idempotent) with a status confirming deletion attempt,
    or 404 if the API layer specifically checks existence before trying to delete and returns 404.
    Based on current understanding of /delete_vector, it should be 200.
    """
    non_existent_point_id = random.randint(9000000, 9999999)  # A high range unlikely to exist

    # The /delete_vector endpoint expects a JSON body like {"point_id": id_value}
    delete_payload = {"point_id": non_existent_point_id}
    response = client.post("/delete_vector", json=delete_payload)

    # Based on the current implementation of /delete_vector and QdrantStore.delete_vector,
    # deleting a non-existent ID returns a 200 OK with status "deleted".
    assert (
        response.status_code == 200
    ), f"Expected status code 200 for deleting non-existent ID, but got {response.status_code}. Response: {response.text}"

    response_json = response.json()
    assert "status" in response_json, "Response JSON should contain a 'status' field."
    assert response_json["status"] == "deleted", f"Expected status 'deleted', but got '{response_json['status']}'"
    assert "point_id" in response_json, "Response JSON should contain a 'point_id' field."
    assert (
        response_json["point_id"] == non_existent_point_id
    ), f"Expected point_id {non_existent_point_id} in response, but got {response_json['point_id']}"

    # To absolutely confirm it's not there, try to get it (should be 404)
    # Corrected: Use POST with JSON body
    get_response = client.post("/get_vector_by_id", json={"point_id": non_existent_point_id})
    assert (
        get_response.status_code == 404
    ), f"Expected 404 when trying to get the supposedly deleted non-existent vector, but got {get_response.status_code}. This indicates it might have somehow been created or the delete logic is different."
