"""
MarcoAI – Application Settings
Reads from the .env file at the repository root.
All values are typed and validated by pydantic-settings.
"""
import logging
import secrets
from functools import lru_cache
from pathlib import Path

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
        """Auto-generate and persist JWT_SECRET if not provided."""
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)
            # Persist to .env for next restart
            env_path = Path(".env")
            if env_path.exists():
                content = env_path.read_text()
                if "SECRET_KEY" not in content:
                    with open(env_path, "a") as f:
                        f.write(f"\nSECRET_KEY={self.secret_key}\n")
                    logger.warning(
                        "JWT_SECRET auto-generated and persisted to .env"
                    )
                else:
                    logger.warning(
                        "SECRET_KEY is empty but exists in .env — "
                        "check your .env file"
                    )
            else:
                logger.warning(
                    "SECRET_KEY not set and no .env file — secret will be "
                    "regenerated on next restart"
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


@lru_cache()
def get_settings() -> Settings:
    """Cached singleton – import and call this everywhere."""
    return Settings()


settings = get_settings()
