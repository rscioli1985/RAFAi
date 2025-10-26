from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from services.backend.models import Organization, User
from .types import OrganizationType, UserType


def _query_organizations(session: Session) -> List[Organization]:
    return (
        session.query(Organization)
        .order_by(Organization.created_at.asc())
        .all()
    )


def resolve_organizations(info) -> List[OrganizationType]:
    session: Session = info.context.session
    organizations = _query_organizations(session)
    return [OrganizationType.from_model(org) for org in organizations]


def resolve_organization_by_slug(slug: str, info) -> Optional[OrganizationType]:
    session: Session = info.context.session
    organization = (
        session.query(Organization)
        .options(joinedload(Organization.roles))
        .filter(Organization.slug == slug)
        .first()
    )
    if not organization:
        return None
    return OrganizationType.from_model(organization)


def resolve_viewer(info) -> Optional[UserType]:
    session: Session = info.context.session
    user = session.query(User).first()
    if not user:
        return None
    return UserType.from_model(user)
