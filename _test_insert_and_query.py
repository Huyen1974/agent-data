# This file is intentionally renamed to _test_insert_and_query.py to prevent pytest discovery.
# It appears to be a standalone script for direct Qdrant interaction, not a standard test.
# Original content is preserved below.

from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue
from qdrant_client.models import PointStruct

client = QdrantClient(
    url="https://ba0aa7ef-be87-47b4-96de-7d36ca4527a8.us-east4-0.gcp.cloud.qdrant.io",
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.3exdWpAbjXl_o11YZHT3Cnlxklkpv5x4InI244BUYV0",
)

client.upsert(
    collection_name="agent_data_vector",
    points=[
        PointStruct(
            id=1, vector=[0.1] * 1536, payload={"source": "test", "tag": "demo"}
        )
    ],
)

print("✅ Đã thêm vector test.")

client.create_payload_index(
    collection_name="agent_data_vector", field_name="tag", field_schema="keyword"
)

print("✅ Đã tạo index cho field 'tag'")

results = client.scroll(
    collection_name="agent_data_vector",
    scroll_filter=Filter(
        must=[FieldCondition(key="tag", match=MatchValue(value="demo"))]
    ),
    limit=5,
)

print("✅ Kết quả truy vấn:")
print(results)
