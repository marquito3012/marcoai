"""
MarcoAI – Application Settings
Reads from the .env file at the repository root.
All values are typed and validated by pydantic-settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Google OAuth ─────────────────────────────────────────────────────────
    google_client_id: str
    google_client_secret: str
    google_api_key: str

    # ── LLM Providers ────────────────────────────────────────────────────────
    groq_api_key: str
    openrouter_api_key: str

    # ── JWT / Security ───────────────────────────────────────────────────────
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 h

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./marcoai.db"

    # ── CORS / Frontend ──────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    # ── Cloudflare ───────────────────────────────────────────────────────────
    cloudflare_tunnel_token: str = ""

    # ── Write-batching (SD protection) ───────────────────────────────────────
    # How often (in seconds) deferred writes should be flushed to SQLite
    write_batch_interval_seconds: int = 60


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton – import and call this everywhere."""
    return Settings()


settings = get_settings()
