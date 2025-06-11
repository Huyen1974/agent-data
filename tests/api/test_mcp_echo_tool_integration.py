import pytest
from tests.mocks.mcp_mock_client import FakeMCPClient


@pytest.fixture
def mcp_mock():
    client = FakeMCPClient()
    client.clear_all_data()
    yield client


@pytest.mark.deferred
def test_mcp_echo_tool_integration(mcp_mock):
    tool_config = {"name": "echo_tool", "type": "echo"}
    mcp_mock.register_tool("echo_tool", tool_config)

    message = {"content": "test message", "tool": "echo_tool"}
    mcp_mock.send_message(message)

    response = mcp_mock.receive_message()
    assert response is not None, "Expected to receive a response"
    assert response["echo"] == message, "Echoed message does not match sent message"
    assert response["status"] == "success", "Expected success status"
    assert mcp_mock._registered_tools["echo_tool"] == tool_config, "Tool registration failed"
