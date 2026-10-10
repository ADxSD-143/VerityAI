"""Runtime configuration.

All fields map to environment variables of the same (lower-cased) name, so
``VERITY_PORT`` sets ``verity_port`` and ``FACTCHECK_API_KEY`` sets
``factcheck_api_key``. Every value has a working default: the core pipeline runs
keyless and offline-from-paid-services.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    verity_host: str = "0.0.0.0"
    verity_port: int = 8000
    verity_cors_origins: str = "*"
    verity_device: str = "cpu"
    verity_torch_threads: int | None = None
    verity_user_agent: str = (
        "VerityAI/0.1 (evidence-grounded fact-checking; +https://github.com/)"
    )
    verity_wikipedia_lang: str = "en"

    verity_bge_model_id: str = "BAAI/bge-small-en-v1.5"
    verity_bge_model_revision: str | None = None
    verity_nli_model_id: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    verity_nli_model_revision: str | None = None
    verity_reranker_model_id: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    verity_reranker_revision: str | None = None

    verity_tau_nli: float = Field(default=0.5, ge=0.0, le=1.0)
    verity_tau_nli_single_source: float = Field(default=0.75, ge=0.0, le=1.0)
    verity_top_k_retrieval: int = Field(default=10, ge=1, le=100)
    verity_top_k_nli: int = Field(default=6, ge=1, le=50)
    verity_max_claims: int = Field(default=5, ge=1, le=20)
    verity_use_reranker: bool = False
    verity_rrf_k: int = Field(default=60, ge=1)
    verity_embed_cache_dir: str | None = None
    verity_preload_models: bool = True

    verity_url_max_bytes: int = 3_000_000
    verity_url_timeout_s: float = 15.0
    verity_source_timeout_s: float = 20.0
    verity_max_pages_per_source: int = 4

    factcheck_api_key: str | None = None
    openalex_mailto: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.verity_cors_origins or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
