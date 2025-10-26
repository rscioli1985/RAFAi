from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class RawPost(BaseModel):
    id: str
    subreddit: str
    author: Optional[str]
    title: Optional[str]
    body: Optional[str]
    score: Optional[int]
    url: Optional[str]
    created_utc: Optional[float]


class RawComment(BaseModel):
    id: str
    post_id: str
    author: Optional[str]
    body: Optional[str]
    score: Optional[int]
    created_utc: Optional[float]


class FAQItem(BaseModel):
    id: Optional[int] = None
    question: str
    answer: Optional[str] = None
    source_post_id: Optional[str] = None
    confidence: Optional[float] = None


class TrackedSubreddit(BaseModel):
    id: int
    name: str
    poll_interval_minutes: int
    last_fetched_at: Optional[datetime]
    keywords: List[str] = Field(default_factory=list)
