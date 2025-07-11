import pytest
from tests.mocks.mcp_mock_client import FakeMCPClient


@pytest.fixture
def mcp_mock():
    client = FakeMCPClient()
    client.clear_all_data()
    yield client


@pytest.mark.unit
def test_mcp_exit_gracefully(mcp_mock):
    # Register a tool and send a message
    tool_config = {"name": "test_tool", "type": "test"}
    mcp_mock.register_tool("test_tool", tool_config)
    mcp_mock.send_message({"content": "test message", "tool": "test_tool"})

    # Verify state before shutdown
    assert len(mcp_mock._registered_tools) == 1, "Expected one registered tool"
    assert not mcp_mock._message_queue.empty(), "Expected non-empty message queue"

    # Shutdown
    mcp_mock.shutdown()

    # Verify state after shutdown
    assert not mcp_mock._is_running, "Expected client to be stopped"
    assert mcp_mock._message_queue.empty(), "Expected empty message queue"
    assert not mcp_mock._registered_tools, "Expected no registered tools"

    # Verify sending message fails
    with pytest.raises(RuntimeError, match="MCP client is not running"):
        mcp_mock.send_message({"content": "post-shutdown message"})
