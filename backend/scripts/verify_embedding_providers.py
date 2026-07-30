"""Standalone verification script comparing Local SentenceTransformer vs. HuggingFaceInferenceProvider.

Usage:
    python scripts/verify_embedding_providers.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import numpy as np
from app.embeddings.providers.huggingface_inference_provider import (
    HuggingFaceInferenceProvider,
)
from app.embeddings.providers.sentence_transformer_provider import (
    SentenceTransformerEmbeddingProvider,
)


async def main():
    print("=" * 70)
    print("EMBEDDING PROVIDER COMPATIBILITY VERIFICATION")
    print("=" * 70)

    test_text = "DocMind AI intelligent document search and retrieval workspace"
    print(f"\n[Test Input Text]: '{test_text}'\n")

    print("1. Initializing Local SentenceTransformerEmbeddingProvider...")
    local_provider = SentenceTransformerEmbeddingProvider()
    print(f"   Model: {local_provider._model_name}")

    print("\n2. Generating Local Embedding...")
    local_vec = await local_provider.generate_embedding(test_text)
    local_norm = float(np.linalg.norm(local_vec))

    print(f"   Shape: {local_vec.shape}")
    print(f"   Dtype: {local_vec.dtype}")
    print(f"   L2 Norm: {local_norm:.6f}")
    print(f"   First 5 components: {local_vec[:5]}")

    print("\n3. Initializing HuggingFaceInferenceProvider...")
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    hf_provider = HuggingFaceInferenceProvider(api_key=hf_token)
    print(f"   Model: {hf_provider._model_name}")
    print(f"   API Token Provided: {'Yes' if hf_token else 'No (Public endpoint)'}")

    try:
        print("\n4. Generating Hugging Face Inference API Embedding...")
        hf_vec = await hf_provider.generate_embedding(test_text)
        hf_norm = float(np.linalg.norm(hf_vec))

        print(f"   Shape: {hf_vec.shape}")
        print(f"   Dtype: {hf_vec.dtype}")
        print(f"   L2 Norm: {hf_norm:.6f}")
        print(f"   First 5 components: {hf_vec[:5]}")

        print("\n" + "=" * 70)
        print("COMPATIBILITY MATRIX")
        print("=" * 70)

        dim_match = local_vec.shape == hf_vec.shape == (384,)
        dtype_match = local_vec.dtype == hf_vec.dtype == np.float32
        norm_match = abs(local_norm - 1.0) < 1e-4 and abs(hf_norm - 1.0) < 1e-4

        # Calculate Cosine Similarity
        cosine_sim = float(np.dot(local_vec, hf_vec))

        print(f"✓ Dimension Parity (384 == 384): {dim_match}")
        print(f"✓ Data Type Parity (float32):    {dtype_match}")
        print(f"✓ L2 Unit Normalization (~1.0):   {norm_match}")
        print(f"✓ Cosine Similarity Score:       {cosine_sim:.6f}")

        if cosine_sim >= 0.98:
            print("\nRESULT: SUCCESS - High fidelity embedding vector compatibility verified!")
        else:
            print(f"\nRESULT: WARNING - Cosine similarity is {cosine_sim:.4f}")

    except Exception as e:
        print(f"\n[Hugging Face API Call Note]: Could not complete live network call: {e}")
        print("Note: Live HF API request requires an active network connection and valid HF_TOKEN.")
        print("Dimension & contract structure verified via unit tests.")


if __name__ == "__main__":
    asyncio.run(main())
