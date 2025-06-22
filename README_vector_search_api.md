# Vector Search API

This API provides a FastAPI endpoint for vector search using the QdrantStore class.

## Prerequisites

- Python 3.7+
- FastAPI
- Uvicorn
- QdrantStore dependencies
- Environment variables set for Qdrant credentials:
  - `QDRANT_API_KEY` - API key for Qdrant service

## Installation

All required dependencies are listed in the project's `requirements.txt`. You can install them with:

```bash
pip install -r requirements.txt
```

## Running the API

To run the API locally:

```bash
python api_vector_search.py
```

This will start a server on `http://127.0.0.1:8000`.

## API Documentation

Once the API is running, you can access the automatic documentation at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Endpoints

### POST /search_vector

Searches for vectors in the Qdrant collection that are similar to the provided query vector.

**Request Body:**

```json
{
  "query_vector": [0.05, 0.05, 0.05, ...],  // 1536 dimensions required
  "top_k": 5,                               // Optional, defaults to 5
  "filter_tag": "unit_test"                 // Optional, filter by tag
}
```

**Response:**

```json
{
  "status": "success",
  "count": 2,
  "results": [
    {
      "id": 1,
      "score": 0.95,
      "payload": {
        "source": "test",
        "tag": "unit_test"
      }
    },
    {
      "id": 2,
      "score": 0.85,
      "payload": {
        "source": "test2",
        "tag": "unit_test"
      }
    }
  ]
}
```

### GET /health

Health check endpoint to verify the API is running.

**Response:**

```json
{
  "status": "healthy"
}
```

## Testing

To run the tests:

```bash
python -m unittest test_api_vector_search.py
```

## Example Usage

Using curl:

```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/search_vector' \
  -H 'Content-Type: application/json' \
  -d '{
  "query_vector": [0.05, 0.05, ..., 0.05],
  "top_k": 5,
  "filter_tag": "unit_test"
}'
```

Using Python requests:

```python
import requests
import json

url = "http://127.0.0.1:8000/search_vector"
payload = {
    "query_vector": [0.05] * 1536,  # 1536-dimensional vector
    "top_k": 5,
    "filter_tag": "unit_test"
}
headers = {"Content-Type": "application/json"}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```
