import json
from queue import Queue
from typing import Any


class FakeMCPClient:
    def __init__(self):
        self._message_queue = Queue()
        self._registered_tools = {}
        self._is_running = True

    def register_tool(self, tool_name: str, tool_config: dict[str, Any]):
        self._registered_tools[tool_name] = tool_config

    def send_message(self, message: dict[str, Any]):
        if self._is_running:
            if (
                message.get("tool") == "echo_tool"
                and "echo_tool" in self._registered_tools
            ):
                # Process echo tool messages directly
                echo_response = self.echo(message)
                self._message_queue.put(json.dumps(echo_response))
            else:
                self._message_queue.put(json.dumps(message))
        else:
            raise RuntimeError("MCP client is not running")

    def receive_message(self) -> dict[str, Any] | None:
        if not self._message_queue.empty():
            return json.loads(self._message_queue.get())
        return None

    def echo(self, message: dict[str, Any]) -> dict[str, Any]:
        return {"echo": message, "status": "success"}

    def shutdown(self):
        self._is_running = False
        # Clear the queue by emptying it.
        # Accessing the underlying deque directly with .queue.clear() is standard.
        with self._message_queue.mutex:
            self._message_queue.queue.clear()
        self._registered_tools.clear()

    def clear_all_data(self):
        # Clear the queue by emptying it.
        with self._message_queue.mutex:
            self._message_queue.queue.clear()
        self._registered_tools.clear()
        self._is_running = True
