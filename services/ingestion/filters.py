from __future__ import annotations

from typing import Iterable


DEFAULT_KEYWORDS: tuple[str, ...] = (
    "NIL",
    "name image likeness",
    "endorsement",
    "collective",
    "compliance",
    "ncaa",
)


def is_nil_relevant(text: str, keywords: Iterable[str] = DEFAULT_KEYWORDS) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)

