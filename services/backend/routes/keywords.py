from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Response
from pydantic import BaseModel, constr
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.backend.models import Keyword
from services.common.db import get_session


router = APIRouter(prefix="/api/keywords", tags=["keywords"])


class KeywordResponse(BaseModel):
    id: int
    term: str
    description: Optional[str]
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, model: Keyword) -> "KeywordResponse":
        return cls(
            id=model.id,
            term=model.term,
            description=model.description,
            status=model.status,
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
        )


class KeywordCreate(BaseModel):
    term: constr(min_length=2, max_length=255)  # type: ignore[valid-type]
    description: Optional[str] = None


class KeywordUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None


def _get_keyword_or_404(session: Session, keyword_id: int) -> Keyword:
    keyword = session.get(Keyword, keyword_id)
    if keyword is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Keyword not found")
    return keyword


@router.get("", response_model=List[KeywordResponse])
def list_keywords(status_filter: Optional[str] = Query(default=None, alias="status"), session: Session = Depends(get_session)) -> List[KeywordResponse]:
    stmt = select(Keyword).order_by(Keyword.term.asc())
    if status_filter:
        stmt = stmt.where(Keyword.status == status_filter)
    rows = session.execute(stmt).scalars().all()
    return [KeywordResponse.from_model(row) for row in rows]


@router.post("", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
def create_keyword(payload: KeywordCreate, session: Session = Depends(get_session)) -> KeywordResponse:
    normalized = payload.term.strip().lower()
    exists = session.execute(select(Keyword).where(Keyword.term == normalized)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Keyword already exists")

    keyword = Keyword(term=normalized, description=payload.description)
    session.add(keyword)
    session.commit()
    session.refresh(keyword)
    return KeywordResponse.from_model(keyword)


@router.put("/{keyword_id}", response_model=KeywordResponse)
def update_keyword(payload: KeywordUpdate, keyword_id: int = Path(..., ge=1), session: Session = Depends(get_session)) -> KeywordResponse:
    keyword = _get_keyword_or_404(session, keyword_id)
    if payload.description is not None:
        keyword.description = payload.description
    if payload.status is not None:
        keyword.status = payload.status
    session.add(keyword)
    session.commit()
    session.refresh(keyword)
    return KeywordResponse.from_model(keyword)


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_keyword(keyword_id: int = Path(..., ge=1), session: Session = Depends(get_session)) -> Response:
    keyword = _get_keyword_or_404(session, keyword_id)
    session.delete(keyword)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
