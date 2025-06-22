"""OpenAI embedding provider implementation."""

import logging
from typing import List, Optional
import os

from .embedding_provider import EmbeddingError
from ..tools.external_tool_registry import get_openai_embedding, OPENAI_AVAILABLE, openai_async_client

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    """OpenAI implementation of the EmbeddingProvider interface.

    This provider wraps the existing OpenAI API integration from external_tool_registry
    to provide a standardized interface for embedding generation.
    """

    def __init__(
        self,
        model_name: str = "text-embedding-ada-002",
        api_key: Optional[str] = None,
        encoding_format: str = "float",
    ):
        """Initialize the OpenAI embedding provider.

        Args:
            model_name: OpenAI embedding model to use
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            encoding_format: Encoding format for embeddings
        """
        self.model_name = model_name
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.encoding_format = encoding_format

        # Validate OpenAI availability
        if not OPENAI_AVAILABLE:
            raise EmbeddingError(
                "OpenAI library not available. Install with: pip install openai", status_code=500, provider="openai"
            )

        if not openai_async_client:
            raise EmbeddingError(
                "OpenAI async client not initialized. Check OPENAI_API_KEY environment variable",
                status_code=500,
                provider="openai",
            )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors, where each vector is a list of floats

        Raises:
            EmbeddingError: When embedding generation fails
        """
        if not texts:
            return []

        try:
            # Use the existing get_openai_embedding function for each text
            embeddings = []
            for text in texts:
                result = await get_openai_embedding(
                    agent_context=None,
                    text_to_embed=text,
                    model_name=self.model_name,
                    encoding_format=self.encoding_format,
                )

                if "error" in result:
                    raise EmbeddingError(
                        f"OpenAI API error: {result['error']}",
                        status_code=result.get("status_code", 500),
                        provider="openai",
                    )

                if "embedding" not in result:
                    raise EmbeddingError("No embedding in OpenAI response", status_code=500, provider="openai")

                embeddings.append(result["embedding"])

            return embeddings

        except EmbeddingError:
            # Re-raise embedding errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI embedding generation: {e}")
            raise EmbeddingError(f"Unexpected error: {str(e)}", status_code=500, provider="openai")

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector as a list of floats

        Raises:
            EmbeddingError: When embedding generation fails
        """
        embeddings = await self.embed([text])
        return embeddings[0] if embeddings else []

    def get_embedding_dimension(self) -> int:
        """Get the dimension size of embeddings produced by this provider.

        Returns:
            Dimension size for OpenAI models
        """
        # Map OpenAI models to their dimensions
        model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return model_dimensions.get(self.model_name, 1536)

    def get_model_name(self) -> str:
        """Get the model name used by this provider.

        Returns:
            Model name string
        """
        return self.model_name


def get_default_embedding_provider() -> OpenAIEmbeddingProvider:
    """Get the default OpenAI embedding provider instance.

    Returns:
        Configured OpenAIEmbeddingProvider instance
    """
    return OpenAIEmbeddingProvider(model_name=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-ada-002"))
