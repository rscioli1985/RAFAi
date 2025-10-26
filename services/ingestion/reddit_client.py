from __future__ import annotations

from typing import Any, Dict, Iterable, List

import praw
from prawcore.exceptions import ResponseException

from services.common import metrics
from services.common.config import settings, load_yaml_secret


class RedditClient:
    def __init__(self) -> None:
        creds = load_yaml_secret(settings.reddit_secrets_file)
        self._reddit = praw.Reddit(
            client_id=creds.get("client_id"),
            client_secret=creds.get("client_secret"),
            user_agent=creds.get("user_agent", "nilrag/0.1"),
            refresh_token=creds.get("refresh_token"),
        )
        # Read-only mode is sufficient for public subreddit reads
        self._reddit.read_only = True

    def fetch_new_posts(self, subreddit: str, limit: int = 50) -> List[Dict[str, Any]]:
        sub = self._reddit.subreddit(subreddit)
        posts: List[Dict[str, Any]] = []
        try:
            for s in sub.new(limit=limit):
                posts.append(
                    {
                        "id": s.id,
                        "title": s.title,
                        "body": s.selftext or "",
                        "url": f"https://www.reddit.com{s.permalink}",
                        "score": int(s.score or 0),
                        "created_utc": float(getattr(s, "created_utc", 0) or 0),
                        "subreddit": str(s.subreddit),
                        "author": str(getattr(s, "author", "") or ""),
                    }
                )
        except ResponseException as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                metrics.record_reddit_rate_limit_hit(subreddit)
            raise

        remaining = None
        auth = getattr(self._reddit, "auth", None)
        if auth is not None:
            limits = getattr(auth, "limits", None)
            if isinstance(limits, dict):
                remaining = limits.get("remaining")
        if remaining is not None and remaining <= 0:
            metrics.record_reddit_rate_limit_hit(subreddit)

        return posts
