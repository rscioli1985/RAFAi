from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from services.backend.models import OrganizationMembership, User
from services.backend.models.organization import UserRole
from services.common.db import get_session
from services.common.security import verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


class OrganizationSummary(BaseModel):
    id: str
    name: str
    slug: str
    role_slugs: List[str]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    user_id: str
    email: EmailStr
    display_name: str | None
    organizations: List[OrganizationSummary]


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> LoginResponse:
    normalized_email = payload.email.lower()
    user = (
        session.query(User)
        .filter(func.lower(User.email) == normalized_email)
        .one_or_none()
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    memberships = (
        session.query(OrganizationMembership)
        .options(
            joinedload(OrganizationMembership.organization),
            joinedload(OrganizationMembership.roles).joinedload(UserRole.role),
        )
        .filter(OrganizationMembership.user_id == user.id, OrganizationMembership.status == "active")
        .all()
    )

    organizations: List[OrganizationSummary] = []
    for membership in memberships:
        org = membership.organization
        if not org:
            continue
        role_slugs = [assignment.role.slug for assignment in membership.roles if assignment.role]
        organizations.append(
            OrganizationSummary(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                role_slugs=role_slugs,
            )
        )

    return LoginResponse(
        user_id=str(user.id),
        email=user.email,
        display_name=user.display_name or user.full_name,
        organizations=organizations,
    )
