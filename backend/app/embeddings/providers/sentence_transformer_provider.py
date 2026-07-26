"""SentenceTransformers embedding provider implementation."""

import asyncio
import logging
from typing import Any, cast

import numpy as np

from app.core.config import get_settings
from app.embeddings.exceptions import EmbeddingGenerationException
from app.embeddings.interfaces.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Embedding provider using SentenceTransformers.

    This provider uses BAAI/bge-small-en-v1.5 model for generating embeddings.
    The model is loaded eagerly during bootstrap and cached for reuse.
    Supports batch generation for efficiency and offloads CPU-bound encoding
    to thread workers via asyncio.to_thread.
    """

    def __init__(self, model_name: str | None = None):
        """Initialize the SentenceTransformers embedding provider.

        Args:
            model_name: The name of the SentenceTransformers model to use.
                        If None, uses EMBEDDING_MODEL from config.
        """
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._model: Any = None
        self._dimension: int | None = None

    def _load_model(self) -> Any:
        """Load the SentenceTransformers model.

        Returns:
            The loaded SentenceTransformer model.
        """
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading SentenceTransformer embedding model: {self._model_name}...")
            self._model = SentenceTransformer(self._model_name)
            if hasattr(self._model, "get_embedding_dimension"):
                self._dimension = self._model.get_embedding_dimension()
            else:
                self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(
                f"SentenceTransformer model {self._model_name} loaded successfully (dim={self._dimension})"
            )
        return self._model

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding for a single text.

        Offloads CPU-bound model.encode to a thread pool via asyncio.to_thread
        to prevent blocking the main asyncio event loop.

        Args:
            text: The text to embed.

        Returns:
            A numpy array representing the embedding vector.

        Raises:
            EmbeddingGenerationException: If embedding generation fails.
        """
        if not text or not text.strip():
            raise EmbeddingGenerationException("Cannot generate embedding for empty text")

        try:
            model = self._load_model()
            embedding = await asyncio.to_thread(model.encode, text, normalize_embeddings=True)
            return cast(np.ndarray, embedding)
        except Exception as e:
            pass
            raise EmbeddingGenerationException(f"Embedding generation failed: {e}")

    async def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts in batch.

        Offloads CPU-bound model.encode to a thread pool via asyncio.to_thread
        to prevent blocking the main asyncio event loop.

        Args:
            texts: List of texts to embed.

        Returns:
            List of numpy arrays representing embedding vectors.

        Raises:
            EmbeddingGenerationException: If embedding generation fails.
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        try:
            model = self._load_model()
            embeddings = await asyncio.to_thread(
                model.encode, valid_texts, normalize_embeddings=True
            )
            return cast(
                list[np.ndarray],
                list(embeddings) if isinstance(embeddings, np.ndarray) else embeddings,
            )
        except Exception as e:
            pass
            raise EmbeddingGenerationException(f"Batch embedding generation failed: {e}")

    def dimension(self) -> int:
        """Get the dimension of the embedding vectors.

        Returns:
            The dimension of the embedding vectors.
        """
        if self._dimension is None:
            self._load_model()
        return cast(int, self._dimension)
