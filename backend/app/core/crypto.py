"""
MarcoAI – Token Encryption Utilities

Uses Fernet symmetric encryption (AES-128-CBC) to encrypt/decrypt
Google OAuth tokens at rest in the database.

The encryption key is read from ENCRYPTION_KEY in the .env file.
"""
from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazy-initialize the Fernet instance from the configured key."""
    global _fernet
    if _fernet is None:
        key = settings.encryption_key.encode() if isinstance(settings.encryption_key, str) else settings.encryption_key
        _fernet = Fernet(key)
    return _fernet


def encrypt_token(plain: str) -> str:
    """Encrypt a plaintext token string. Returns a Fernet token (starts with 'gAAAAA')."""
    if not plain:
        return plain
    f = _get_fernet()
    return f.encrypt(plain.encode()).decode()


def decrypt_token(cipher: str) -> str:
    """Decrypt a Fernet-encrypted token string back to plaintext."""
    if not cipher:
        return cipher
    f = _get_fernet()
    try:
        return f.decrypt(cipher.encode()).decode()
    except InvalidToken:
        # Token is not encrypted (legacy plaintext) — return as-is
        logger.warning("Token is not encrypted or key mismatch; returning raw value.")
        return cipher


def is_encrypted(value: str) -> bool:
    """Check if a value looks like a Fernet-encrypted token."""
    return value.startswith("gAAAAA")
