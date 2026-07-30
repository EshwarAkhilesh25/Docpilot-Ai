"""Interface for embedding providers."""

from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation.

    This interface defines the foundational contract for generating text embeddings
    across both Document Ingestion and Chat Pipeline retrieval.

    Contract Specifications:
    - Expected Dimension: 384 (for BAAI/bge-small-en-v1.5)
    - Vector Normalization: L2 normalized vectors (length 1.0) required for FAISS Inner Product similarity search
    - Output Format: numpy.ndarray with dtype float32

    Future Migration Note:
    Swapping provider implementations (e.g. from local PyTorch to Hugging Face Inference API)
    will conform to this exact interface contract without requiring downstream code changes.
    """

    @abstractmethod
    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding for a single text.

        Args:
            text: The text to embed.

        Returns:
            A numpy array representing the embedding vector.

        Raises:
            EmbeddingGenerationException: If embedding generation fails.
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed.

        Returns:
            List of numpy arrays representing embedding vectors.

        Raises:
            EmbeddingGenerationException: If embedding generation fails.
        """
        pass

    @abstractmethod
    def dimension(self) -> int:
        """Get the dimension of the embedding vectors.

        Returns:
            The dimension of the embedding vectors.
        """
        pass
