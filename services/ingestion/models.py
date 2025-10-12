from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


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

