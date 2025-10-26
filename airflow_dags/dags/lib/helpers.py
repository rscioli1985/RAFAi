from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def match_keywords(post: Dict[str, Any], keywords: List[str]) -> bool:
    if not keywords:
        return True
    haystack = f"{post.get('title', '')} {post.get('body', '')}".lower()
    return any(keyword in haystack for keyword in keywords)


def to_datetime(timestamp: Any) -> datetime | None:
    if not timestamp:
        return None
    try:
        seconds = float(timestamp)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc)
