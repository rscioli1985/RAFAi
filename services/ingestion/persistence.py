from __future__ import annotations

import uuid
from typing import Dict, Iterable

from sqlalchemy.orm import Session

from services.backend.models import Analysis, Post


def persist_posts(session: Session, *, job_id: uuid.UUID, organization_id: uuid.UUID, posts: Iterable[Dict]) -> int:
    inserted = 0
    for post in posts:
        exists = session.query(Post).filter(Post.external_id == post["external_id"]).first()
        if exists:
            continue
        session.add(
            Post(
                job_id=job_id,
                organization_id=organization_id,
                external_id=post["external_id"],
                subreddit=post["subreddit"],
                author=post.get("author"),
                title=post.get("title"),
                body=post.get("body"),
                url=post.get("url"),
                posted_at=post.get("posted_at"),
                score=post.get("score"),
            )
        )
        inserted += 1
    return inserted


def persist_analysis(session: Session, *, job_id: uuid.UUID, records: Iterable[Dict]) -> int:
    inserted = 0
    for record in records:
        session.add(
            Analysis(
                job_id=job_id,
                post_id=record.get("post_id"),
                model=record.get("model"),
                summary=record.get("summary"),
                sentiment=record.get("sentiment"),
                metadata_json=record.get("metadata_json"),
            )
        )
        inserted += 1
    return inserted
