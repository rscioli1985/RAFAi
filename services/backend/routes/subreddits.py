from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Response
from pydantic import BaseModel, conint, constr
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.backend.models import Subreddit, Keyword, SubredditKeyword
from services.common.db import get_session


router = APIRouter(prefix="/api/subreddits", tags=["subreddits"])


class SubredditResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    poll_interval_minutes: int
    last_fetched_at: Optional[str]
    last_post_id: Optional[str]
    created_at: str
    updated_at: str
    keywords: List[int] = []

    @classmethod
    def from_model(cls, model: Subreddit) -> "SubredditResponse":
        keyword_ids = [assoc.keyword_id for assoc in model.keywords]
        return cls(
            id=model.id,
            name=model.name,
            description=model.description,
            status=model.status,
            poll_interval_minutes=model.poll_interval_minutes,
            last_fetched_at=model.last_fetched_at.isoformat() if model.last_fetched_at else None,
            last_post_id=model.last_post_id,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
            keywords=keyword_ids,
        )


class SubredditCreate(BaseModel):
    name: constr(min_length=3, max_length=255)  # type: ignore[valid-type]
    description: Optional[str] = None
    poll_interval_minutes: conint(ge=30, le=1440 * 7) = 1440  # type: ignore[valid-type]
    keyword_ids: Optional[List[int]] = None


class SubredditUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    poll_interval_minutes: Optional[conint(ge=30, le=1440 * 7)] = None  # type: ignore[valid-type]
    keyword_ids: Optional[List[int]] = None


def _get_subreddit_or_404(session: Session, subreddit_id: int) -> Subreddit:
    subreddit = session.get(Subreddit, subreddit_id)
    if subreddit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subreddit not found")
    return subreddit


@router.get("", response_model=List[SubredditResponse])
def list_subreddits(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
) -> List[SubredditResponse]:
    stmt = select(Subreddit).order_by(Subreddit.created_at.asc())
    if status_filter:
        stmt = stmt.where(Subreddit.status == status_filter)
    rows = session.execute(stmt).scalars().all()
    return [SubredditResponse.from_model(row) for row in rows]


@router.post("", response_model=SubredditResponse, status_code=status.HTTP_201_CREATED)
def create_subreddit(payload: SubredditCreate, session: Session = Depends(get_session)) -> SubredditResponse:
    normalized = payload.name.strip().lstrip("r/").lower()
    exists = session.execute(select(Subreddit).where(Subreddit.name == normalized)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Subreddit already tracked")

    subreddit = Subreddit(
        name=normalized,
        description=payload.description,
        poll_interval_minutes=payload.poll_interval_minutes,
    )
    session.add(subreddit)
    session.flush()

    if payload.keyword_ids:
        keywords = (
            session.query(Keyword)
            .filter(Keyword.id.in_(payload.keyword_ids))
            .all()
        )
        for keyword in keywords:
            session.add(SubredditKeyword(subreddit_id=subreddit.id, keyword_id=keyword.id))

    session.commit()
    session.refresh(subreddit)
    return SubredditResponse.from_model(subreddit)


@router.put("/{subreddit_id}", response_model=SubredditResponse)
def update_subreddit(
    payload: SubredditUpdate,
    subreddit_id: int = Path(..., ge=1),
    session: Session = Depends(get_session),
) -> SubredditResponse:
    subreddit = _get_subreddit_or_404(session, subreddit_id)
    if payload.description is not None:
        subreddit.description = payload.description
    if payload.status is not None:
        subreddit.status = payload.status
    if payload.poll_interval_minutes is not None:
        subreddit.poll_interval_minutes = payload.poll_interval_minutes

    if payload.keyword_ids is not None:
        session.query(SubredditKeyword).filter(SubredditKeyword.subreddit_id == subreddit.id).delete()
        if payload.keyword_ids:
            keywords = (
                session.query(Keyword)
                .filter(Keyword.id.in_(payload.keyword_ids))
                .all()
            )
            for keyword in keywords:
                session.add(SubredditKeyword(subreddit_id=subreddit.id, keyword_id=keyword.id))

    session.add(subreddit)
    session.commit()
    session.refresh(subreddit)
    return SubredditResponse.from_model(subreddit)


@router.delete("/{subreddit_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_subreddit(subreddit_id: int = Path(..., ge=1), session: Session = Depends(get_session)) -> Response:
    subreddit = _get_subreddit_or_404(session, subreddit_id)
    session.delete(subreddit)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
