"""SentenceTransformers embedding provider implementation.

Legacy Local Embedding Provider

This provider generates embeddings using SentenceTransformer
(BAAI/bge-small-en-v1.5) running locally with PyTorch.

It has been retained for reference purposes.

Reason for replacement:
- Render Free Tier provides only 512 MB RAM.
- PyTorch + SentenceTransformer consumes approximately
  340–370 MB during inference.
- Combined with FastAPI, SQLAlchemy, FAISS, and application
  runtime, peak RSS exceeds Render's memory limit, causing
  Linux OOM termination.

Production deployments should instead use the
Hugging Face Inference API provider to eliminate
local PyTorch memory usage.

Do not remove this implementation unless we intentionally
drop support for local embeddings.

Current Flow:
Text -> SentenceTransformer.encode() -> 384-dimensional normalized vector -> FAISS Index

Note: Both document ingestion and query retrieval rely on this provider.

Planned Migration Architecture:
Current:
  SentenceTransformer -> PyTorch -> Local inference
Future:
  EmbeddingProvider -> Hugging Face Inference API -> HTTP request -> 384-dimensional embedding

Key Architecture Notes:
- The EmbeddingProvider interface remains unchanged.
- Only the provider implementation will change.
- Document ingestion and query embedding will continue to share the exact same abstraction.
"""

import asyncio
import logging
import threading
from typing import Any, cast

import numpy as np

from app.core.config import get_settings
from app.embeddings.exceptions import EmbeddingGenerationException
from app.embeddings.interfaces.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Legacy Local Embedding Provider using SentenceTransformers.

    This provider uses BAAI/bge-small-en-v1.5 model for generating embeddings.
    The model is loaded lazily on demand and cached for reuse. Model loading
    and CPU-bound encoding are offloaded to worker threads via asyncio.to_thread,
    ensuring that FastAPI's main asyncio event loop remains fully responsive
    to health checks and HTTP traffic during initial load.
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
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    def _load_model_sync(self) -> Any:
        """Synchronously load the SentenceTransformers model with thread-safe locking."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    logger.info(
                        f"Loading SentenceTransformer embedding model: {self._model_name}..."
                    )
                    model = SentenceTransformer(self._model_name)
                    if hasattr(model, "get_embedding_dimension"):
                        dimension = model.get_embedding_dimension()
                    else:
                        dimension = model.get_sentence_embedding_dimension()

                    self._dimension = dimension
                    self._model = model
                    logger.info(
                        f"SentenceTransformer model {self._model_name} loaded successfully (dim={self._dimension})"
                    )
        return self._model

    async def _get_model(self) -> Any:
        """Asynchronously get or load the model without blocking the asyncio event loop."""
        if self._model is not None:
            return self._model

        async with self._async_lock:
            if self._model is None:
                await asyncio.to_thread(self._load_model_sync)

        return self._model

    def _load_model(self) -> Any:
        """Synchronous load_model interface for backward compatibility."""
        return self._load_model_sync()

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding for a single text.

        Offloads model loading and CPU-bound model.encode to worker threads via
        asyncio.to_thread to prevent blocking the main asyncio event loop.

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
            model = await self._get_model()
            embedding = await asyncio.to_thread(model.encode, text, normalize_embeddings=True)
            return cast(np.ndarray, embedding)
        except Exception as e:
            pass
            raise EmbeddingGenerationException(f"Embedding generation failed: {e}")

    async def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts in batch.

        Offloads model loading and CPU-bound model.encode to worker threads via
        asyncio.to_thread to prevent blocking the main asyncio event loop.

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
            model = await self._get_model()
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
            self._load_model_sync()
        return cast(int, self._dimension)
