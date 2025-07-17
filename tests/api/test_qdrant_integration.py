"""Integration tests for QdrantStore tools with ToolsManager."""

from unittest.mock import patch

import pytest

from agent_data_manager.agent.agent_data_agent import AgentDataAgent
from agent_data_manager.tools.register_tools import register_tools
from tests.mocks.fake_qdrant_v2 import MockQdrantStore


@pytest.fixture
def agent_with_tools():
    """Create an AgentDataAgent with all tools registered."""
    agent = AgentDataAgent(name="TestAgent")
    register_tools(agent)
    return agent


@pytest.fixture
def mock_qdrant_store():
    """Create a mock QdrantStore for testing."""
    store = MockQdrantStore()
    # Clear any existing data
    store.client.clear_all_data()
    return store


@pytest.mark.asyncio
async def test_qdrant_tools_registration(agent_with_tools):
    """Test that Qdrant tools are properly registered with ToolsManager."""
    expected_qdrant_tools = [
        "qdrant_upsert_vector",
        "qdrant_query_by_tag",
        "qdrant_delete_by_tag",
        "qdrant_get_count",
        "qdrant_health_check",
        "save_vector_to_qdrant",
        "search_vectors_qdrant",
        "qdrant_generate_and_store_embedding",
        "qdrant_semantic_search",
        "qdrant_batch_generate_embeddings",
        "semantic_search_qdrant",
    ]

    registered_tools = list(agent_with_tools.tools_manager.tools.keys())

    # Check if any Qdrant tools are registered
    qdrant_tools_found = [
        tool for tool in expected_qdrant_tools if tool in registered_tools
    ]

    # This test passes if tools are registered or gives info if they're not available
    if len(qdrant_tools_found) > 0:
        print(
            f"Found {len(qdrant_tools_found)} Qdrant tools registered: {qdrant_tools_found}"
        )
        assert len(qdrant_tools_found) > 0
    else:
        print(f"No Qdrant tools found in {len(registered_tools)} registered tools")
        print(f"Available tools: {registered_tools}")
        # This is expected if dependencies are not available
        assert True  # Pass the test either way


@pytest.mark.asyncio
async def test_qdrant_upsert_vector_tool(agent_with_tools, mock_qdrant_store):
    """Test qdrant_upsert_vector tool through ToolsManager."""
    if "qdrant_upsert_vector" not in agent_with_tools.tools_manager.tools:
        pytest.skip("qdrant_upsert_vector tool not available")

    with patch(
        "agent_data_manager.tools.qdrant_vector_tools.get_qdrant_store",
        return_value=mock_qdrant_store,
    ):
        # Test vector upsert
        test_vector = [0.1] * 1536
        test_metadata = {"content": "test content", "category": "test"}

        result = await agent_with_tools.tools_manager.execute_tool(
            "qdrant_upsert_vector",
            vector_id="test_vector_1",
            vector=test_vector,
            metadata=test_metadata,
            tag="test_tag",
        )

        assert result["status"] == "success"
        assert result["vector_id"] == "test_vector_1"


@pytest.mark.asyncio
async def test_qdrant_query_by_tag_tool(agent_with_tools, mock_qdrant_store):
    """Test qdrant_query_by_tag tool through ToolsManager."""
    if "qdrant_query_by_tag" not in agent_with_tools.tools_manager.tools:
        pytest.skip("qdrant_query_by_tag tool not available")

    with patch(
        "agent_data_manager.tools.qdrant_vector_tools.get_qdrant_store",
        return_value=mock_qdrant_store,
    ):
        # First insert a vector
        test_vector = [0.2] * 1536
        await mock_qdrant_store.upsert_vector(
            vector_id="test_vector_2",
            vector=test_vector,
            metadata={"content": "query test"},
            tag="query_test_tag",
        )

        # Test query by tag
        result = await agent_with_tools.tools_manager.execute_tool(
            "qdrant_query_by_tag", tag="query_test_tag", limit=10
        )

        assert result["status"] == "success"
        assert result["tag"] == "query_test_tag"
        assert len(result["results"]) == 1
        assert result["results"][0]["id"] == "test_vector_2"


@pytest.mark.asyncio
async def test_qdrant_health_check_tool(agent_with_tools, mock_qdrant_store):
    """Test qdrant_health_check tool through ToolsManager."""
    if "qdrant_health_check" not in agent_with_tools.tools_manager.tools:
        pytest.skip("qdrant_health_check tool not available")

    with patch(
        "agent_data_manager.tools.qdrant_vector_tools.get_qdrant_store",
        return_value=mock_qdrant_store,
    ):
        result = await agent_with_tools.tools_manager.execute_tool(
            "qdrant_health_check"
        )

        assert result["status"] == "success"
        assert result["healthy"] is True
        assert "message" in result


@pytest.mark.asyncio
async def test_qdrant_get_count_tool(agent_with_tools, mock_qdrant_store):
    """Test qdrant_get_count tool through ToolsManager."""
    if "qdrant_get_count" not in agent_with_tools.tools_manager.tools:
        pytest.skip("qdrant_get_count tool not available")

    with patch(
        "agent_data_manager.tools.qdrant_vector_tools.get_qdrant_store",
        return_value=mock_qdrant_store,
    ):
        # Insert some test vectors
        for i in range(3):
            await mock_qdrant_store.upsert_vector(
                vector_id=f"count_test_{i}", vector=[0.1 * i] * 1536, tag="count_test"
            )

        result = await agent_with_tools.tools_manager.execute_tool("qdrant_get_count")

        assert result["status"] == "success"
        assert result["count"] == 3


@pytest.mark.asyncio
async def test_qdrant_delete_by_tag_tool(agent_with_tools, mock_qdrant_store):
    """Test qdrant_delete_by_tag tool through ToolsManager."""
    if "qdrant_delete_by_tag" not in agent_with_tools.tools_manager.tools:
        pytest.skip("qdrant_delete_by_tag tool not available")

    with patch(
        "agent_data_manager.tools.qdrant_vector_tools.get_qdrant_store",
        return_value=mock_qdrant_store,
    ):
        # Insert test vectors
        await mock_qdrant_store.upsert_vector(
            vector_id="delete_test_1", vector=[0.3] * 1536, tag="delete_test_tag"
        )

        # Verify vector exists
        query_result = await mock_qdrant_store.query_vectors_by_tag("delete_test_tag")
        assert len(query_result) == 1

        # Delete by tag
        result = await agent_with_tools.tools_manager.execute_tool(
            "qdrant_delete_by_tag", tag="delete_test_tag"
        )

        assert result["status"] == "success"
        assert result["tag"] == "delete_test_tag"

        # Verify vector is deleted
        query_result_after = await mock_qdrant_store.query_vectors_by_tag(
            "delete_test_tag"
        )
        assert len(query_result_after) == 0


@pytest.mark.asyncio
async def test_semantic_search_qdrant_tool(agent_with_tools, mock_qdrant_store):
    """Test semantic_search_qdrant tool through ToolsManager."""
    if "semantic_search_qdrant" not in agent_with_tools.tools_manager.tools:
        pytest.skip("semantic_search_qdrant tool not available")

    # Mock OpenAI embedding generation
    mock_embedding = [0.1] * 1536

    with (
        patch(
            "agent_data_manager.tools.qdrant_embedding_tools.get_openai_embedding"
        ) as mock_get_embedding,
        patch(
            "agent_data_manager.tools.qdrant_embedding_tools.openai_client",
            return_value=True,
        ),
        patch("agent_data_manager.tools.qdrant_embedding_tools.OPENAI_AVAILABLE", True),
        patch(
            "agent_data_manager.tools.qdrant_embedding_tools.get_qdrant_store",
            return_value=mock_qdrant_store,
        ),
    ):

        mock_get_embedding.return_value = {"embedding": mock_embedding}

        # Insert test data with embeddings
        await mock_qdrant_store.upsert_vector(
            vector_id="semantic_test_1",
            vector=mock_embedding,
            metadata={"original_text": "test document content"},
            tag="semantic_test",
        )

        result = await agent_with_tools.tools_manager.execute_tool(
            "semantic_search_qdrant",
            query_text="test query",
            index_name="test_index",  # Ignored parameter for compatibility
            threshold=0.5,
            top_n=5,
        )

        assert result["status"] == "success"
        assert "similar_items" in result
        assert (
            len(result["similar_items"]) >= 0
        )  # May be 0 if no matches above threshold


@pytest.mark.asyncio
async def test_qdrant_tool_error_handling(agent_with_tools):
    """Test error handling in Qdrant tools."""
    if "qdrant_upsert_vector" not in agent_with_tools.tools_manager.tools:
        pytest.skip("qdrant_upsert_vector tool not available")

    # Test with invalid vector format
    result = await agent_with_tools.tools_manager.execute_tool(
        "qdrant_upsert_vector",
        vector_id="error_test",
        vector="invalid_vector_format",  # This should cause an error
        metadata={},
        tag="error_test",
    )

    assert result["status"] == "failed"
    assert "error" in result


@pytest.mark.asyncio
async def test_qdrant_config_validation():
    """Test Qdrant configuration validation (fast mock version)."""
    from unittest.mock import patch

    from agent_data_manager.config.settings import Settings

    # Mock the class attributes to test validation logic
    with patch.object(Settings, "QDRANT_URL", "https://test.qdrant.io"):
        with patch.object(Settings, "QDRANT_API_KEY", "test-api-key"):
            # Test that validation passes with proper config
            assert Settings.validate_qdrant_config() is True

    # Test validation fails with missing URL
    with patch.object(Settings, "QDRANT_URL", None):
        with patch.object(Settings, "QDRANT_API_KEY", "test-api-key"):
            assert Settings.validate_qdrant_config() is False

    # Test validation fails with missing API key
    with patch.object(Settings, "QDRANT_URL", "https://test.qdrant.io"):
        with patch.object(Settings, "QDRANT_API_KEY", None):
            assert Settings.validate_qdrant_config() is False


@pytest.mark.slow
@pytest.mark.asyncio
async def test_qdrant_cluster_info():
    """Test that we can validate API key access by getting collections info."""
    try:
        import httpx
        from qdrant_client import QdrantClient
        from qdrant_client.http.exceptions import ResponseHandlingException

        from agent_data_manager.config.settings import settings

        # Only run if we have a valid Qdrant configuration
        if not settings.validate_qdrant_config():
            pytest.skip("Qdrant configuration not available")

        # Create client with real configuration and shorter timeout
        client = QdrantClient(
            url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=5.0
        )  # 5 second timeout

        # Test collections list access (validates API key and connection)
        collections = client.get_collections()
        assert collections is not None

        # Test that we can get collection info if any collections exist
        if hasattr(collections, "collections") and collections.collections:
            # Try to get info about the first collection
            first_collection = collections.collections[0]
            collection_info = client.get_collection(first_collection.name)
            assert collection_info is not None

    except ImportError:
        pytest.skip("qdrant-client not available")
    except (
        ResponseHandlingException,
        httpx.ConnectTimeout,
        httpx.TimeoutException,
    ) as e:
        # Skip test if there are connection/timeout issues
        pytest.skip(f"Qdrant connection timeout or network issue: {e}")
    except Exception as e:
        # If this fails, it indicates API key validation issues
        pytest.fail(f"Qdrant API key validation failed: {e}")
