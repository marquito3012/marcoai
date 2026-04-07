"""
Memory-efficient configuration with lazy loading.
Optimized for Raspberry Pi 3 (1GB RAM).
"""
import os
from functools import lru_cache
from typing import Optional


class Settings:
    """
    Application settings with minimal memory footprint.
    Uses __slots__ to prevent dynamic attribute creation.
    """
    __slots__ = (
        '_app_name', '_debug', '_log_level',
        '_database_url', '_data_dir',
        '_groq_api_key', '_openrouter_api_key', '_gemini_api_key',
        '_google_client_id', '_google_client_secret',
        '_default_model', '_fallback_model',
        '_max_memory_mb', '_sqlite_cache_size',
        '_secret_key', '_app_url',
    )

    def __init__(self):
        # Core
        self._app_name = "Marco AI"
        self._debug = os.getenv("DEBUG", "false").lower() == "true"
        self._log_level = os.getenv("LOG_LEVEL", "WARNING")

        # Database - single SQLite file for minimal overhead
        self._data_dir = os.getenv("DATA_DIR", "./data")
        self._database_url = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{self._data_dir}/marcoai.db"
        )

        # LLM APIs - rotation order for graceful degradation
        self._groq_api_key = os.getenv("GROQ_API_KEY", "")
        self._openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self._gemini_api_key = os.getenv("GEMINI_API_KEY", "")

        # Default to fastest/cheapest first
        self._default_model = "groq/llama-3.3-70b-versatile"
        self._fallback_model = "openrouter/meta-llama/llama-3-8b-instruct"

        # Google OAuth
        self._google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self._google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")

        # Session security & public URL
        self._secret_key = os.getenv("SECRET_KEY", "change-me-in-production-use-random-32-chars")
        self._app_url = os.getenv("APP_URL", "http://localhost:8000")

        # Memory limits - CRITICAL for Raspberry Pi 3
        self._max_memory_mb = int(os.getenv("MAX_MEMORY_MB", "512"))
        self._sqlite_cache_size = int(os.getenv("SQLITE_CACHE_SIZE", "2000"))  # 2MB page cache

    @property
    def app_name(self) -> str:
        return self._app_name

    @property
    def debug(self) -> bool:
        return self._debug

    @property
    def log_level(self) -> str:
        return self._log_level

    @property
    def database_url(self) -> str:
        return self._database_url

    @property
    def data_dir(self) -> str:
        return self._data_dir

    @property
    def groq_api_key(self) -> Optional[str]:
        return self._groq_api_key if self._groq_api_key else None

    @property
    def openrouter_api_key(self) -> Optional[str]:
        return self._openrouter_api_key if self._openrouter_api_key else None

    @property
    def gemini_api_key(self) -> Optional[str]:
        return self._gemini_api_key if self._gemini_api_key else None

    @property
    def llm_api_order(self) -> list:
        """Return API providers in priority order for fallback."""
        providers = []
        if self._groq_api_key:
            providers.append("groq")
        if self._openrouter_api_key:
            providers.append("openrouter")
        if self._gemini_api_key:
            providers.append("gemini")
        return providers

    @property
    def google_client_id(self) -> Optional[str]:
        return self._google_client_id

    @property
    def google_client_secret(self) -> Optional[str]:
        return self._google_client_secret

    @property
    def secret_key(self) -> str:
        return self._secret_key

    @property
    def app_url(self) -> str:
        return self._app_url

    @property
    def max_memory_mb(self) -> int:
        return self._max_memory_mb

    @property
    def sqlite_cache_size(self) -> int:
        return self._sqlite_cache_size


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached settings getter - only instantiated once.
    Uses lru_cache to prevent multiple instantiations.
    """
    return Settings()
