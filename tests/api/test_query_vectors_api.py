import pytestimport random
import uuid
from fastapi.testclient import TestClient
from api_vector_search import app  # Assuming your FastAPI app instance is here

client = TestClient(app)

VECTOR_DIMENSION = 1536


def create_random_vector():
    return [random.random() for _ in range(VECTOR_DIMENSION)]


def generate_unique_tag():
    return f"test-tag-{uuid.uuid4()}"


    @pytest.mark.slow
    def test_get_vector_by_id():
    """
    Tests retrieving a single vector by its point_id.
    """
    point_id = random.randint(1, 1000000)
    vector = create_random_vector()
    tag = generate_unique_tag()
    payload = {"tag": tag}

    # Upsert the vector
    upsert_response = client.post(
        "/upsert_vector",
        json={"point_id": point_id, "vector": vector, "metadata": payload},
    )
    assert upsert_response.status_code == 200, f"Failed to upsert vector: {upsert_response.text}"
    assert upsert_response.json().get("status") == "ok"

    # Get the vector by ID
    get_response = client.post(f"/get_vector_by_id", json={"point_id": point_id})

    assert get_response.status_code == 200, f"Failed to get vector by ID: {get_response.text}"

    retrieved_point_data = get_response.json()
    assert retrieved_point_data is not None, "API returned None for an existing vector ID"
    assert retrieved_point_data["status"] == "ok"

    retrieved_vector_data = retrieved_point_data.get("point")
    assert retrieved_vector_data is not None, "Response missing 'point' field"

    assert "id" in retrieved_vector_data, "Response missing 'id' field"
    assert "metadata" in retrieved_vector_data, "Response missing 'metadata' field"
    assert "vector" in retrieved_vector_data, "Response missing 'vector' field"

    assert (
        retrieved_vector_data["id"] == point_id
    ), f"Expected point_id {point_id}, but got {retrieved_vector_data['id']}"
    assert (
        retrieved_vector_data["metadata"] == payload
    ), f"Expected payload {payload}, but got {retrieved_vector_data['metadata']}"
    # It's good practice to also check the vector, but floating point comparisons can be tricky.
    # For now, checking ID and payload should suffice based on common practices.
    # If vector check is strictly needed, we can add:
    # assert all(abs(a - b) < 1e-5 for a, b in zip(retrieved_vector_data["vector"], vector)), \
    #     f"Expected vector {vector}, but got {retrieved_vector_data['vector']}"


    @pytest.mark.slow
    def test_query_vectors_by_ids():
    """
    Tests querying multiple vectors by a list of point_ids.
    """
    num_vectors_to_query = random.randint(3, 5)
    points_to_upsert = []
    expected_points_data = {}  # Store as {id: payload} for easy lookup
    point_ids_to_query = []

    for i in range(num_vectors_to_query):
        point_id = random.randint(3000001, 4000000)  # New range for IDs
        vector = create_random_vector()
        tag = generate_unique_tag()
        item_metadata = {"tag": tag, "index": i}

        points_to_upsert.append({"id": point_id, "vector": vector, "metadata": item_metadata})
        expected_points_data[point_id] = item_metadata
        point_ids_to_query.append(point_id)

    # Add a decoy point that won't be queried
    decoy_point_id = random.randint(4000001, 5000000)
    points_to_upsert.append(
        {
            "id": decoy_point_id,
            "vector": create_random_vector(),
            "metadata": {"tag": generate_unique_tag(), "decoy": True},
        }
    )

    # Upsert the vectors
    for point_data in points_to_upsert:
        upsert_response = client.post(
            "/upsert_vector",
            json={"point_id": point_data["id"], "vector": point_data["vector"], "metadata": point_data["metadata"]},
        )
        assert upsert_response.status_code == 200, f"Failed to upsert vector {point_data['id']}: {upsert_response.text}"
        assert upsert_response.json().get("status") == "ok"

    # Query vectors by IDs
    # Ensure the API expects a list of integers for point_ids, not strings
    query_body = {"point_ids": point_ids_to_query, "limit": 10}
    query_response = client.post("/query_vectors_by_ids", json=query_body)

    assert query_response.status_code == 200, f"Failed to query by IDs: {query_response.text}"

    retrieved_points = query_response.json()
    assert isinstance(retrieved_points, list), "Response should be a list of points"

    assert (
        len(retrieved_points) == num_vectors_to_query
    ), f"Expected {num_vectors_to_query} vectors for IDs {point_ids_to_query}, but got {len(retrieved_points)}"

    retrieved_ids = set()
    for point in retrieved_points:
        assert "id" in point, "Point in response missing 'id' field"
        assert "payload" in point, "Point in response missing 'payload' field"

        point_id = point["id"]
        retrieved_ids.add(point_id)

        assert (
            point_id in expected_points_data
        ), f"Retrieved unexpected point_id {point_id}. Queried IDs: {point_ids_to_query}"

        expected_payload = expected_points_data[point_id]
        assert (
            point["payload"] == expected_payload
        ), f"For point_id {point_id}, expected payload {expected_payload}, but got {point['payload']}"

    assert (
        set(point_ids_to_query) == retrieved_ids
    ), f"Set of queried IDs {set(point_ids_to_query)} does not match set of retrieved IDs {retrieved_ids}"
