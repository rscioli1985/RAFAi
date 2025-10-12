from __future__ import annotations

from typing import Any, Dict, Iterable, List

import praw

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
        posts = []
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
        return posts
