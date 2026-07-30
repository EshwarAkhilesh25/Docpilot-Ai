"""Hugging Face Inference API embedding provider implementation with resilience retries."""

import asyncio
import logging
import os
import random
from typing import Any, cast

import httpx
import numpy as np

from app.core.config import get_settings
from app.embeddings.exceptions import EmbeddingGenerationException
from app.embeddings.interfaces.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class HuggingFaceInferenceProvider(EmbeddingProvider):
    """Embedding provider using Hugging Face Inference API.

    Generates 384-dimensional float32 L2-normalized embeddings for BAAI/bge-small-en-v1.5
    via HTTP requests without loading local PyTorch / SentenceTransformers model weights.
    Reduces local process RAM usage from ~370MB down to ~0MB.

    Resilience & Batching Features:
    - Single HTTP POST request per batch (partitions into sub-batches of max 32 texts if needed)
    - Automatic exponential backoff + jitter for HTTP 429 (Rate Limit) & HTTP 5xx errors
    - Automatic retry handling for HTTP 503 (Model Loading / Warmup)
    - Configurable request timeouts
    - Structured logging
    """

    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
    EXPECTED_DIMENSION = 384
    MAX_BATCH_SIZE = 32
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.5

    def __init__(self, model_name: str | None = None, api_key: str | None = None):
        """Initialize the Hugging Face Inference API embedding provider.

        Args:
            model_name: Hugging Face model identifier (defaults to BAAI/bge-small-en-v1.5).
            api_key: Optional Hugging Face API token (HF_TOKEN or HUGGINGFACE_API_KEY).
        """
        self._model_name = model_name or getattr(settings, "EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._api_key = (
            api_key
            or getattr(settings, "HUGGINGFACE_API_KEY", None)
            or os.getenv("HUGGINGFACE_API_KEY")
            or os.getenv("HF_TOKEN")
            or ""
        )
        self._dimension = self.EXPECTED_DIMENSION
        self._timeout = float(getattr(settings, "HF_TIMEOUT", 30.0))

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        """L2-normalize vector to unit length for FAISS compatibility."""
        vector = vector.astype(np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _process_response_data(self, raw_data: Any, expected_count: int) -> list[np.ndarray]:
        """Convert raw response data (OpenAI-compatible or feature extraction format) into normalized numpy arrays."""
        # 1. OpenAI-style Embeddings Format: {"data": [{"embedding": [...]}, ...]}
        if isinstance(raw_data, dict) and "data" in raw_data and isinstance(raw_data["data"], list):
            results = []
            for item in raw_data["data"]:
                vec = np.array(item["embedding"], dtype=np.float32)
                results.append(self._normalize(vec))
            return results

        # 2. Feature Extraction Array Format
        arr = np.array(raw_data, dtype=np.float32)

        # Single vector (1D)
        if arr.ndim == 1 and arr.shape[0] == self._dimension:
            return [self._normalize(arr)]

        # Single token matrix (2D) -> Mean pooling
        if arr.ndim == 2 and arr.shape[0] != expected_count and arr.shape[1] == self._dimension:
            pooled = np.mean(arr, axis=0)
            return [self._normalize(pooled)]

        # Batch vectors (2D)
        if arr.ndim == 2 and arr.shape[1] == self._dimension:
            return [self._normalize(vec) for vec in arr]

        # Batch token matrices (3D)
        if arr.ndim == 3 and arr.shape[2] == self._dimension:
            return [self._normalize(np.mean(item, axis=0)) for item in arr]

        raise EmbeddingGenerationException(
            f"Unexpected embedding shape from HuggingFace API: {arr.shape}, expected count: {expected_count}, dim: {self._dimension}"
        )

    async def _post_with_resilience(
        self, client: httpx.AsyncClient, payload: dict[str, Any]
    ) -> Any:
        """Execute HTTP POST with retries, exponential backoff, 429 rate limit handling, and 503 warmup retries."""
        # Try modern Hugging Face router API first, fallback to feature extraction endpoint
        endpoints = [
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self._model_name}",
            f"https://api-inference.huggingface.co/models/{self._model_name}",
            f"https://router.huggingface.co/hf-inference/v1/embeddings",
        ]

        last_exception: Exception | None = None

        for endpoint in endpoints:
            headers = self._get_headers()

            # Adapt payload format for endpoint type
            if "router.huggingface.co" in endpoint:
                request_body = {
                    "model": self._model_name,
                    "input": payload["inputs"],
                }
            else:
                request_body = {
                    "inputs": payload["inputs"],
                    "options": {"wait_for_model": True},
                }

            for attempt in range(1, self.MAX_RETRIES + 1):
                try:
                    logger.debug(
                        f"HF API request attempt {attempt}/{self.MAX_RETRIES} to {endpoint}"
                    )
                    response = await client.post(
                        endpoint, headers=headers, json=request_body, timeout=self._timeout
                    )

                    # Success (200 OK)
                    if response.status_code == 200:
                        return response.json()

                    # Handle 503 Model Loading / Warmup
                    if response.status_code == 503:
                        logger.info(
                            f"HuggingFace model '{self._model_name}' is currently loading (HTTP 503). Retrying in 3s... (attempt {attempt})"
                        )
                        await asyncio.sleep(3.0)
                        continue

                    # Handle 429 Rate Limit
                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after")
                        delay = (
                            float(retry_after)
                            if retry_after and retry_after.isdigit()
                            else (self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1)))
                            + random.uniform(0.1, 0.5)
                        )
                        logger.warning(
                            f"HuggingFace API rate limit hit (HTTP 429). Retrying in {delay:.2f}s... (attempt {attempt})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Handle 5xx Server Errors
                    if response.status_code >= 500:
                        delay = (self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1))) + random.uniform(
                            0.1, 0.5
                        )
                        logger.warning(
                            f"HuggingFace API server error HTTP {response.status_code}. Retrying in {delay:.2f}s... (attempt {attempt})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # For 4xx errors other than 429, don't retry same endpoint
                    logger.error(
                        f"HuggingFace API client error HTTP {response.status_code}: {response.text}"
                    )
                    break

                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    delay = (self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1))) + random.uniform(
                        0.1, 0.5
                    )
                    logger.warning(
                        f"HuggingFace API network/timeout error: {e}. Retrying in {delay:.2f}s... (attempt {attempt})"
                    )
                    last_exception = e
                    await asyncio.sleep(delay)

        raise EmbeddingGenerationException(
            f"HuggingFace embedding request failed after retries across endpoints: {last_exception or 'Invalid response'}"
        )

    async def generate_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding for a single text via Hugging Face Inference API."""
        if not text or not text.strip():
            raise EmbeddingGenerationException("Cannot generate embedding for empty text")

        payload = {"inputs": text}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            raw_data = await self._post_with_resilience(client, payload)
            vectors = self._process_response_data(raw_data, expected_count=1)
            return vectors[0]

    async def generate_embeddings(self, texts: list[str]) -> list[np.ndarray]:
        """Generate embeddings for multiple texts in batch via Hugging Face Inference API.

        Performs single HTTP POST request per batch (chunking into sub-batches of MAX_BATCH_SIZE).
        """
        if not texts:
            return []

        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        # Partition into sub-batches of max size (e.g. 32)
        batches = [
            valid_texts[i : i + self.MAX_BATCH_SIZE]
            for i in range(0, len(valid_texts), self.MAX_BATCH_SIZE)
        ]

        all_vectors: list[np.ndarray] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for batch in batches:
                payload = {"inputs": batch}
                raw_data = await self._post_with_resilience(client, payload)
                vectors = self._process_response_data(raw_data, expected_count=len(batch))
                all_vectors.extend(vectors)

        return all_vectors

    def dimension(self) -> int:
        """Get vector dimension (384 for BAAI/bge-small-en-v1.5)."""
        return self._dimension

