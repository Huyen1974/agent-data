"""EmbeddingProvider protocol for abstracting embedding operations."""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers to abstract embedding operations.

    This interface allows the Agent Data system to switch between different
    embedding providers (e.g., OpenAI, Vertex AI) without changing the core logic.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors, where each vector is a list of floats

        Raises:
            EmbeddingError: When embedding generation fails
        """
        ...

    async def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as a list of floats

        Raises:
            EmbeddingError: When embedding generation fails
        """
        ...

    def get_embedding_dimension(self) -> int:
        """Get the dimension size of embeddings produced by this provider.

        Returns:
            Dimension size (e.g., 1536 for OpenAI text-embedding-ada-002)
        """
        ...

    def get_model_name(self) -> str:
        """Get the model name used by this provider.

        Returns:
            Model name string
        """
        ...


class EmbeddingError(Exception):
    """Exception raised when embedding generation fails."""

    def __init__(self, message: str, status_code: int = 500, provider: str = "unknown"):
        self.message = message
        self.status_code = status_code
        self.provider = provider
        super().__init__(self.message)
