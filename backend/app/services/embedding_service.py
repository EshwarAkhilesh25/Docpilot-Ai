"""Service for generating embeddings."""

import logging

import numpy as np

from app.embeddings.interfaces.embedding_provider import EmbeddingProvider
from app.services.exceptions import DocumentProcessingException

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings for text chunks.

    This service coordinates the generation of embeddings for text chunks
    using the embedding provider. It handles batch generation for efficiency.
    """

    def __init__(self, embedding_provider: EmbeddingProvider):
        """Initialize the embedding service.

        Args:
            embedding_provider: The embedding provider to use.
        """
        self._embedding_provider = embedding_provider

    async def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            DocumentProcessingException: If embedding generation fails.
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} text item(s)")
            embeddings = await self._embedding_provider.generate_embeddings(texts)
            logger.info(f"Generated {len(embeddings)} embedding vector(s)")
            return embeddings

        except Exception as e:
            logger.exception("Embedding generation failed: %s", e)
            raise DocumentProcessingException(f"Embedding generation failed: {e}")
