"""
config.py — Centralised settings loaded from environment / .env file.
Uses pydantic-settings so every field is type-validated at startup.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────────────────────────────────
    supabase_url: str = Field(default="", description="Supabase project URL")
    supabase_key: str = Field(default="", description="Supabase anon/public key")
    supabase_service_role_key: str = Field(
        default="", description="Supabase service-role key (server-side only)"
    )
    supabase_jwt_secret: str = Field(default="", description="Supabase JWT secret")

    # ── FastAPI ─────────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_base_url: str = Field(default="http://localhost:8000")

    # ── Flask Dashboard ─────────────────────────────────────────────────────────
    flask_port: int = Field(default=5000)
    flask_secret_key: str = Field(default="change-me-in-production")

    # ── Face Recognition ────────────────────────────────────────────────────────
    face_match_threshold: float = Field(
        default=0.6, description="Cosine distance threshold; lower = stricter"
    )

    # ── Logging ─────────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
