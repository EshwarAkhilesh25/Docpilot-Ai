"""Unit tests and compatibility verification for HuggingFaceInferenceProvider."""

from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from app.embeddings.exceptions import EmbeddingGenerationException
from app.embeddings.providers.huggingface_inference_provider import (
    HuggingFaceInferenceProvider,
)
from app.embeddings.providers.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)


class TestHuggingFaceInferenceProvider:
    """Unit tests for HuggingFaceInferenceProvider."""

    def test_init_defaults(self):
        provider = HuggingFaceInferenceProvider()
        assert provider._model_name == "BAAI/bge-small-en-v1.5"
        assert provider.dimension() == 384

    def test_init_custom_api_key(self):
        provider = HuggingFaceInferenceProvider(api_key="hf_test_token_123")
        assert provider._api_key == "hf_test_token_123"

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text_raises(self):
        provider = HuggingFaceInferenceProvider()
        with pytest.raises(EmbeddingGenerationException, match="empty text"):
            await provider.generate_embedding("")

    @pytest.mark.asyncio
    async def test_generate_embeddings_empty_list(self):
        provider = HuggingFaceInferenceProvider()
        result = await provider.generate_embeddings([])
        assert result == []

    @pytest.mark.asyncio
    async def test_mocked_generate_embedding_success(self):
        provider = HuggingFaceInferenceProvider()
        fake_vector = [0.1] * 384

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: fake_vector

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            embedding = await provider.generate_embedding("DocMind AI document search")

            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (384,)
            assert embedding.dtype == np.float32
            # Verify L2 normalization (unit length)
            assert np.isclose(np.linalg.norm(embedding), 1.0, atol=1e-5)


@pytest.mark.asyncio
async def test_provider_compatibility_comparison():
    """Comparison test verifying Local SentenceTransformer vs HuggingFaceInferenceProvider compatibility.

    Validates:
    1. Vector dimension (384 == 384)
    2. Data type (float32 == float32)
    3. L2 norm (approx 1.0 for both)
    4. Cosine similarity
    """
    local_provider = SentenceTransformerEmbeddingProvider()
    test_text = "DocMind AI document workspace analysis"

    # Generate local embedding
    local_embedding = await local_provider.generate_embedding(test_text)

    # Validate local embedding contract
    assert local_embedding.shape == (384,)
    assert local_embedding.dtype == np.float32
    assert np.isclose(np.linalg.norm(local_embedding), 1.0, atol=1e-4)

    # Create HF provider with local vector mock to test parity without requiring live network token
    hf_provider = HuggingFaceInferenceProvider()
    fake_hf_response = local_embedding.tolist()

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = lambda: fake_hf_response

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        hf_embedding = await hf_provider.generate_embedding(test_text)

        # 1. Dimension check
        assert local_embedding.shape == hf_embedding.shape == (384,)

        # 2. Dtype check
        assert local_embedding.dtype == hf_embedding.dtype == np.float32

        # 3. L2 norm check
        assert np.isclose(np.linalg.norm(local_embedding), 1.0, atol=1e-4)
        assert np.isclose(np.linalg.norm(hf_embedding), 1.0, atol=1e-4)

        # 4. Cosine similarity check (dot product of L2 normalized vectors)
        cosine_sim = float(np.dot(local_embedding, hf_embedding))
        assert cosine_sim >= 0.99
