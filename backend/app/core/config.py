"""
MarcoAI – Application Settings
Reads from the .env file at the repository root.
All values are typed and validated by pydantic-settings.
"""
import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 h

    def model_post_init(self, __context) -> None:
        """Fail fast unless SECRET_KEY is stable.

        SECRET_KEY signs JWTs; regenerating it on every restart invalidates
        sessions and encrypted tokens. The app never auto-generates it — the
        operator must set a value of at least 32 characters in .env.
        """
        if not self.secret_key or len(self.secret_key) < 32:
            raise RuntimeError(
                "SECRET_KEY must be set in .env with at least 32 characters "
                "(e.g. a 32+ char random string from `python -c "
                "\"import secrets; print(secrets.token_urlsafe(32))\"`). "
                "MarcoAI refuses to start without a stable signing key."
            )

    # ── Encryption (Fernet key for Google OAuth tokens at rest) ─────────────
    encryption_key: str

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./marcoai.db"

    # ── CORS / Frontend ──────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    # ── Cloudflare ───────────────────────────────────────────────────────────
    cloudflare_tunnel_token: str = ""

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_rpm: int = 30  # Max requests per minute per user

    # ── Write-batching (SD protection) ───────────────────────────────────────
    # How often (in seconds) deferred writes should be flushed to SQLite
    write_batch_interval_seconds: int = 60

    # ── RAG Document Processing ──────────────────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton – import and call this everywhere."""
    return Settings()


settings = get_settings()
