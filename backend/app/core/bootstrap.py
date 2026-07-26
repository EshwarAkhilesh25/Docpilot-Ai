"""Application bootstrap for infrastructure initialization.

This module handles centralized infrastructure initialization and graceful shutdown.
It is responsible for setting up storage, FAISS index, provider factories, and database verification at application startup.
No business logic should be added here.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.db.migration_verification import MigrationVerificationError, MigrationVerifier

logger = logging.getLogger(__name__)
settings = get_settings()


class ProviderRegistry:
    """Registry for provider factories.

    This allows lazy provider creation and decouples bootstrap from provider implementations.
    """

    def __init__(self):
        """Initialize the provider registry."""
        self._factories: dict[str, Callable[[], Any]] = {}
        self._instances: dict[str, Any] = {}

    def register(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a provider factory.

        Args:
            name: The name of the provider.
            factory: A callable that creates the provider instance.
        """
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        """Get or create a provider instance.

        Args:
            name: The name of the provider.

        Returns:
            The provider instance.

        Raises:
            KeyError: If provider factory is not registered.
        """
        if name not in self._factories:
            raise KeyError(f"Provider factory not registered: {name}")

        if name not in self._instances:
            self._instances[name] = self._factories[name]()

        return self._instances[name]

    def has(self, name: str) -> bool:
        """Check if a provider factory is registered.

        Args:
            name: The name of the provider.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._factories

    def clear(self) -> None:
        """Clear all provider instances (useful for testing)."""
        self._instances.clear()


class Bootstrap:
    """Centralized application bootstrap for infrastructure initialization.

    This class handles:
    - Configuration validation
    - Storage directory verification
    - Provider factory registration
    - Graceful shutdown
    """

    def __init__(self):
        """Initialize the bootstrap."""
        self._initialized = False
        self._provider_registry = ProviderRegistry()

    def validate_configuration(self) -> None:
        """Validate application configuration.

        Raises:
            ValueError: If required configuration is invalid.
        """
        pass

        # Validate required fields for production
        if settings.APP_ENV == "production":
            if settings.JWT_SECRET == "change-this-secret-in-production":
                raise ValueError("JWT_SECRET must be changed in production")
            if not settings.GROQ_API_KEY:
                pass

        # Validate storage path
        storage_path = Path(settings.STORAGE_PATH)
        if not storage_path.is_absolute():
            pass

        # Validate FAISS index path
        faiss_path = Path(settings.FAISS_INDEX_PATH)
        if not faiss_path.is_absolute():
            pass

        pass

    def verify_storage_directories(self) -> None:
        """Verify and create storage directories.

        Raises:
            OSError: If directories cannot be created.
        """
        storage_path = Path(settings.STORAGE_PATH)
        storage_path.mkdir(parents=True, exist_ok=True)

        faiss_path = Path(settings.FAISS_INDEX_PATH)
        faiss_path.mkdir(parents=True, exist_ok=True)

        bm25_path = Path(settings.BM25_INDEX_PATH)
        bm25_path.mkdir(parents=True, exist_ok=True)

    def verify_database_migrations(self) -> None:
        """Verify database migration status.

        This checks if the database schema is at the latest migration.
        In strict mode, pending migrations will cause startup to fail.

        Raises:
            MigrationVerificationError: If verification fails and strict mode is enabled.
        """
        pass

        try:
            verifier = MigrationVerifier()
            status = verifier.verify_migrations()

            # Log migration status
            pass

            # Handle pending migrations based on strict mode
            if status["has_pending_migrations"]:
                if settings.STRICT_MIGRATION_CHECK:
                    error_msg = (
                        f"Pending migrations detected. "
                        f"Current: {status['current_revision']}, Head: {status['head_revision']}. "
                        f"Run migrations before starting."
                    )
                    pass
                    raise MigrationVerificationError(error_msg)
                else:
                    pass

            # Handle database unreachable
            if status["error"] and "unreachable" in status["error"].lower():
                pass
                raise MigrationVerificationError(f"Database unreachable: {status['error']}")

            # Handle no migrations found
            if status["error"] and "not initialized" in status["error"].lower():
                pass
                if settings.STRICT_MIGRATION_CHECK:
                    raise MigrationVerificationError(
                        "Database not initialized - run migrations first"
                    )

        except MigrationVerificationError:
            raise
        except Exception as e:
            pass
            if settings.STRICT_MIGRATION_CHECK:
                raise MigrationVerificationError(f"Migration verification failed: {e}")

    def register_provider_factories(self) -> None:
        """Register provider factories for lazy initialization.

        This decouples bootstrap from provider implementations.
        Providers are created on first use.
        """
        pass

        # Storage provider factory
        from app.storage.providers.local_storage_provider import LocalStorageProvider

        self._provider_registry.register(
            "storage", lambda: LocalStorageProvider(settings.STORAGE_PATH)
        )

        # Embedding provider factory
        from app.embeddings.providers.sentence_transformer_provider import (
            SentenceTransformerEmbeddingProvider,
        )

        self._provider_registry.register(
            "embedding", lambda: SentenceTransformerEmbeddingProvider(settings.EMBEDDING_MODEL)
        )

        # Vector index provider factory
        from pathlib import Path

        from app.vectorstore.providers.faiss_provider import FAISSVectorProvider

        self._provider_registry.register(
            "vector_index",
            lambda: FAISSVectorProvider(
                index_path=str(Path(settings.FAISS_INDEX_PATH) / "index.faiss")
            ),
        )

        # Keyword index provider factory (BM25)
        from app.keyword_search.providers.bm25_provider import BM25Provider

        def create_keyword_index():
            index_file = str(Path(settings.BM25_INDEX_PATH) / "bm25_index.pkl")
            provider = BM25Provider(index_path=index_file)
            try:
                # Need to load the index on startup to avoid overwriting it later
                provider.load_index(index_file)
            except Exception:
                pass
            return provider

        self._provider_registry.register("keyword_index", create_keyword_index)
        pass

        # LLM provider factory (optional - depends on API key)
        if settings.GROQ_API_KEY:
            from app.chat.providers.groq_provider import GroqLLMProvider

            self._provider_registry.register("llm", lambda: GroqLLMProvider())
            pass
        else:
            pass

        # Transcription provider factory (optional - depends on API key)
        if settings.GROQ_API_KEY:
            from app.ingestion.providers.whisper_transcription_provider import (
                WhisperTranscriptionProvider,
            )

            self._provider_registry.register(
                "transcription", lambda: WhisperTranscriptionProvider()
            )
            pass
        else:
            pass

    async def shutdown(self) -> None:
        """Gracefully shutdown all infrastructure components.

        This method closes HTTP clients, releases resources, and performs cleanup.
        Shutdown continues even if individual providers fail to close.
        """
        pass

        # Define all provider names that might need cleanup
        provider_names = [
            "llm",
            "transcription",
            "embedding",
            "vector_index",
            "storage",
            "keyword_index",
        ]

        for provider_name in provider_names:
            if self._provider_registry.has(provider_name):
                try:
                    provider = self._provider_registry.get(provider_name)
                    if hasattr(provider, "close"):
                        # Check if close is async or sync
                        import inspect

                        if inspect.iscoroutinefunction(provider.close):
                            await provider.close()
                        else:
                            provider.close()
                        pass
                except Exception:
                    pass

        # Clear provider instances
        self._provider_registry.clear()

        pass

    def get_llm_provider(self):
        """Get the LLM provider instance (created lazily).

        Returns:
            The LLM provider or None if not registered.
        """
        if not self._provider_registry.has("llm"):
            return None
        return self._provider_registry.get("llm")

    def get_embedding_provider(self):
        """Get the embedding provider instance (created lazily).

        Returns:
            The embedding provider or None if not registered.
        """
        if not self._provider_registry.has("embedding"):
            return None
        return self._provider_registry.get("embedding")

    def get_transcription_provider(self):
        """Get the transcription provider instance (created lazily).

        Returns:
            The transcription provider or None if not registered.
        """
        if not self._provider_registry.has("transcription"):
            return None
        return self._provider_registry.get("transcription")

    def get_storage_provider(self):
        """Get the storage provider instance (created lazily).

        Returns:
            The storage provider or None if not registered.
        """
        if not self._provider_registry.has("storage"):
            return None
        return self._provider_registry.get("storage")

    def get_vector_index_provider(self):
        """Get the vector index provider instance (created lazily).

        Returns:
            The vector index provider or None if not registered.
        """
        if not self._provider_registry.has("vector_index"):
            return None
        return self._provider_registry.get("vector_index")

    def get_keyword_index_provider(self):
        """Get the keyword index provider instance (created lazily).

        Returns:
            The keyword index provider or None if not registered.
        """
        if not self._provider_registry.has("keyword_index"):
            return None
        return self._provider_registry.get("keyword_index")

    def log_startup_info(self) -> None:
        """Log startup information.

        This logs application version, enabled providers, and paths.
        Sensitive information like API keys is never logged.
        """
        pass

        pass

        pass


# Global bootstrap instance
_bootstrap: Bootstrap | None = None


def get_bootstrap() -> Bootstrap:
    """Get the global bootstrap instance.

    Returns:
        The global Bootstrap instance.
    """
    global _bootstrap
    if _bootstrap is None:
        _bootstrap = Bootstrap()
    return _bootstrap


async def initialize_application() -> Bootstrap:
    """Initialize the application infrastructure.

    This is the main entry point for application startup.
    It performs configuration validation, directory verification,
    database migration verification, provider factory registration,
    eagerly loads the embedding model, and logs startup information.

    Returns:
        The initialized Bootstrap instance.

    Raises:
        ValueError: If configuration is invalid.
        OSError: If directories cannot be created.
        MigrationVerificationError: If migration verification fails in strict mode.
    """
    bootstrap = get_bootstrap()

    bootstrap.validate_configuration()
    bootstrap.verify_storage_directories()
    bootstrap.verify_database_migrations()
    bootstrap.register_provider_factories()
    bootstrap.log_startup_info()

    return bootstrap


async def shutdown_application() -> None:
    """Shutdown the application infrastructure.

    This should be called during application shutdown to ensure
    graceful cleanup of resources.
    """
    bootstrap = get_bootstrap()
    await bootstrap.shutdown()
