from __future__ import annotations

import re
from typing import Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HANDLE_RE = re.compile(r"u/[A-Za-z0-9_-]+")


def sanitize_text(value: Optional[str]) -> str:
    """Lightweight PII scrub for Reddit content before LLM processing."""
    if not value:
        return ""
    text = EMAIL_RE.sub("[email]", value)
    text = HANDLE_RE.sub("u/[redacted]", text)
    return text.strip()
