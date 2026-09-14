"""Filename sanitisation helpers (stdlib only — safe to import anywhere)."""

_SAFE_PUNCT = "._- ()"


def sanitize_filename(filename: str) -> str:
    """Reduce a user-supplied filename to a safe basename for local storage.

    Strips any POSIX/Windows path components, keeps letters/digits/spaces plus
    a small allow-list of punctuation, and never returns an empty, '.' or '..'
    result (which would be identical to a parent-directory reference).
    """
    if not filename or filename in (".", ".."):
        return "unnamed"
    base = filename.replace("\\", "/").split("/")[-1]
    cleaned = "".join(ch if (ch.isalnum() or ch in _SAFE_PUNCT) else "-" for ch in base)
    cleaned = cleaned.strip(" ")
    return cleaned if cleaned not in ("", ".", "..") else "unnamed"
