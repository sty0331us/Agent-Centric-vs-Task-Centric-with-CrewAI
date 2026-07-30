"""Customer query validation and sanitization."""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_MAX_QUERY_CHARS = 500

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE = re.compile(r"\s+")


@dataclass(slots=True)
class ValidationResult:
    """Outcome of validating a customer query."""

    ok: bool
    query: str = ""
    error: str | None = None


def sanitize_query(raw: str, *, max_chars: int = DEFAULT_MAX_QUERY_CHARS) -> ValidationResult:
    """
    Normalize and bound a customer query before it reaches any crew.

    Rejects empty input and oversized payloads; strips control characters.
    """
    if raw is None:
        return ValidationResult(ok=False, error="Please type a question.")

    cleaned = _CONTROL_CHARS.sub("", raw)
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()
    if not cleaned:
        return ValidationResult(ok=False, error="Please type a question.")
    if len(cleaned) > max_chars:
        return ValidationResult(
            ok=False,
            error=f"Please keep your question under {max_chars} characters.",
        )
    return ValidationResult(ok=True, query=cleaned)
