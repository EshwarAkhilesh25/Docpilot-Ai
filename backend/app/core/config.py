from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "DocMind API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://postgres:eshwar@localhost:5432/docmind")
    DB_POOL_SIZE: int = Field(default=5, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Pool recycle timeout in seconds")
    DB_POOL_PRE_PING: bool = Field(default=True, description="Enable connection pre-ping")
    DB_ECHO: bool = Field(default=False, description="Echo SQL statements")
    STRICT_MIGRATION_CHECK: bool = Field(
        default=False, description="Fail startup if migrations are pending"
    )

    # Security
    JWT_SECRET: str = Field(default="change-this-secret-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days

    # AI Services
    GROQ_API_KEY: str = Field(default="")
    HUGGINGFACE_API_KEY: str = Field(default="", description="Hugging Face API Token for remote inference")

    # LLM Configuration
    LLM_TIMEOUT: float = Field(default=60.0)
    LLM_TEMPERATURE: float = Field(default=0.7)
    LLM_MAX_TOKENS: int = Field(default=1024)
    LLM_MAX_RETRIES: int = Field(default=3)
    LLM_RETRY_DELAY: float = Field(default=1.0)
    LLM_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # RAG Configuration
    RAG_MIN_SIMILARITY_THRESHOLD: float = Field(default=0.05)
    RAG_MAX_CONTEXT_CHUNKS: int = Field(default=10)
    RAG_FALLBACK_RESPONSE: str = Field(
        default="I don't have enough information in the uploaded documents."
    )

    # Hybrid Retrieval Configuration
    HYBRID_RETRIEVAL_ENABLED: bool = Field(
        default=True, description="Enable hybrid retrieval (semantic + keyword)"
    )
    SEMANTIC_TOP_K: int = Field(default=20, description="Number of semantic search candidates")
    KEYWORD_TOP_K: int = Field(default=20, description="Number of keyword search candidates")
    MERGED_TOP_K: int = Field(
        default=20, description="Number of merged results after hybrid retrieval"
    )
    BM25_INDEX_PATH: str = Field(
        default="storage/bm25_index", description="Path for BM25 index storage"
    )
    SEMANTIC_WEIGHT: float = Field(default=1.0, description="Weight for semantic retrieval scores")
    KEYWORD_WEIGHT: float = Field(default=1.0, description="Weight for keyword retrieval scores")

    # Storage Configuration
    STORAGE_PATH: str = Field(default="storage/uploads")
    FAISS_INDEX_PATH: str = Field(default="storage/faiss_index")

    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-small-en-v1.5")

    # Transcription Configuration
    WHISPER_MODEL: str = Field(default="whisper-large-v3")
    TRANSCRIPTION_TIMEOUT: float = Field(default=300.0)
    TRANSCRIPTION_MAX_RETRIES: int = Field(default=3)
    TRANSCRIPTION_RETRY_DELAY: float = Field(default=2.0)

    # Supabase
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # CORS
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://localhost:3001"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = Field(default=["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default=["*"])

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("APP_ENV")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"APP_ENV must be one of {valid_envs}")
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()


@lru_cache
def get_settings() -> Settings:
    return Settings()
