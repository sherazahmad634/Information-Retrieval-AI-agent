"""Application configuration loaded from environment variables.

Uses pydantic-settings to provide a single, validated, type-safe `Settings`
object that is injected throughout the application via dependency injection.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Application -------------------------------------------------------
    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "ir-agent"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # ---- CORS --------------------------------------------------------------
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ---- Auth --------------------------------------------------------------
    api_key: str | None = None
    rate_limit_per_minute: int = 60

    # ---- LLM ---------------------------------------------------------------
    llm_provider: Literal["openai", "anthropic", "mock"] = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    anthropic_api_key: str | None = None
    mock_llm: bool = False

    # ---- Web Search --------------------------------------------------------
    web_search_provider: Literal["duckduckgo", "tavily"] = "duckduckgo"
    tavily_api_key: str | None = None

    # ---- Embeddings --------------------------------------------------------
    embedding_provider: Literal["sentence-transformers", "openai", "mock"] = "sentence-transformers"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # ---- Reranker ----------------------------------------------------------
    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ---- Vector store ------------------------------------------------------
    vector_store_provider: Literal["chroma", "memory"] = "chroma"
    vector_store_path: str = "./data/chroma"
    vector_store_collection: str = "ir_agent_docs"

    # ---- Document store ----------------------------------------------------
    document_store_path: str = "./data/documents.db"

    # ---- Ingestion ---------------------------------------------------------
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_upload_size_mb: int = 25

    # ---- Retrieval ---------------------------------------------------------
    top_k_retrieval: int = 20
    top_k_rerank: int = 5
    hybrid_alpha: float = 0.5
    rrf_k: int = 60

    # ---- Seed corpus -------------------------------------------------------
    seed_corpus_path: str = "./data/seed"

    @field_validator("cors_origins")
    @classmethod
    def _validate_cors(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def use_mock_llm(self) -> bool:
        """Return True if a mock LLM should be used (no external calls)."""
        return self.mock_llm or self.llm_provider == "mock"

    def ensure_data_dirs(self) -> None:
        """Create persistence directories on startup."""
        Path(self.vector_store_path).mkdir(parents=True, exist_ok=True)
        Path(self.document_store_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton settings instance."""
    settings = Settings()
    settings.ensure_data_dirs()
    return settings
