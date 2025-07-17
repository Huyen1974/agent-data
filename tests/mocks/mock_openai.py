"""
Mock OpenAI implementation for testing.
Prevents test failures due to OpenAI API configuration or rate limits.
CLI119D4 - Mock OpenAI API calls.
"""

from typing import Any


class MockChatCompletion:
    """Mock implementation of OpenAI ChatCompletion."""

    @staticmethod
    def create(*args, **kwargs) -> dict[str, Any]:
        """Mock ChatCompletion.create method."""
        # Extract model and messages if provided
        model = kwargs.get("model", "gpt-3.5-turbo")
        messages = kwargs.get("messages", [])

        # Generate a simple mock response based on the input
        if messages:
            last_message = messages[-1] if isinstance(messages, list) else {}
            content = last_message.get("content", "test query")
        else:
            content = "test query"

        # Simple mock response generation
        mock_response = f"Mock response for: {content[:50]}..."

        return {
            "id": "chatcmpl-mock123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": mock_response},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
        }


class MockEmbeddings:
    """Mock implementation of OpenAI Embeddings."""

    @staticmethod
    def create(*args, **kwargs) -> dict[str, Any]:
        """Mock Embeddings.create method."""
        input_text = kwargs.get("input", "test input")
        model = kwargs.get("model", "text-embedding-ada-002")

        # Generate a mock embedding vector (1536 dimensions for ada-002)
        import hashlib
        import struct

        # Create deterministic embedding based on input text
        if isinstance(input_text, list):
            embeddings = []
            for i, text in enumerate(input_text):
                # Generate deterministic vector based on text hash
                text_hash = hashlib.md5(str(text).encode()).digest()
                # Convert to 1536 float values between -1 and 1
                vector = []
                for j in range(1536):
                    byte_index = (j * 4) % len(text_hash)
                    value = struct.unpack(
                        "f",
                        text_hash[byte_index : byte_index + 4]
                        * (4 // len(text_hash[byte_index : byte_index + 4]) + 1),
                    )[0]
                    # Normalize to [-1, 1]
                    vector.append(max(-1.0, min(1.0, value / 1000000)))

                embeddings.append(
                    {"object": "embedding", "index": i, "embedding": vector}
                )
        else:
            # Single text input
            text_hash = hashlib.md5(str(input_text).encode()).digest()
            vector = []
            for j in range(1536):
                byte_index = (j * 4) % len(text_hash)
                # Simple deterministic float generation
                value = (hash(str(input_text) + str(j)) % 2000000 - 1000000) / 1000000
                vector.append(max(-1.0, min(1.0, value)))

            embeddings = [{"object": "embedding", "index": 0, "embedding": vector}]

        return {
            "object": "list",
            "data": embeddings,
            "model": model,
            "usage": {
                "prompt_tokens": len(str(input_text)),
                "total_tokens": len(str(input_text)),
            },
        }


class MockOpenAI:
    """Mock OpenAI client."""

    def __init__(self, *args, **kwargs):
        self.chat = MockChat()
        self.embeddings = MockEmbeddings()


class MockChat:
    """Mock chat completions."""

    def __init__(self):
        self.completions = MockChatCompletion()


def patch_openai():
    """Patch OpenAI imports with mock implementations."""
    import sys

    # Create mock openai module
    mock_openai = type(sys)("openai")
    mock_openai.OpenAI = MockOpenAI
    mock_openai.ChatCompletion = MockChatCompletion
    mock_openai.Embedding = MockEmbeddings

    # Patch sys.modules
    sys.modules["openai"] = mock_openai

    return mock_openai


# Auto-patch if OPENAI_API_KEY is set to dummy
import os

if os.getenv("OPENAI_API_KEY") == "dummy":
    patch_openai()
