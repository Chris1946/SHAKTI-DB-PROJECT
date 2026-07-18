"""
PulseTrace Backend — Centralized Configuration

Uses Pydantic BaseSettings to load configuration from environment
variables with validation, type coercion, and sensible defaults.

All configuration is accessed through the singleton `settings` object:
    from app.config import settings
    print(settings.database_url)
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "PulseTrace"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # ---- Database ----
    database_url: str = (
        os.getenv("DATABASE_URL") or 
        "postgresql+asyncpg://postgres@localhost:5432/shakthidb"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_echo: bool = False

    # ---- Server ----
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ---- Security ----
    api_key: str = ""
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ---- Agent Defaults ----
    collection_interval: int = 5
    top_processes: int = 10

    # ---- Alert Thresholds (Rule Engine) ----
    alert_cpu_critical: float = 90.0
    alert_cpu_warning: float = 80.0
    alert_memory_critical: float = 95.0
    alert_memory_warning: float = 85.0
    alert_disk_critical: float = 90.0
    alert_disk_warning: float = 80.0

    # ---- LLM Configuration ----
    llm_provider: str = "grok"
    llm_model: str = "llama-3.3-70b-versatile"
    llm_api_key: str = "" # Alias for GROQ_API_KEY
    llm_temperature: float = 0.15
    llm_top_p: float = 0.9
    llm_max_tokens: int = 1200
    llm_timeout: int = 30


    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Accept CORS origins as JSON string or list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def api_key_enabled(self) -> bool:
        """API key authentication is enabled when a key is set."""
        return bool(self.api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


# Convenience alias
settings = get_settings()
