from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import strawberry
from strawberry.types import Info
from sqlalchemy.orm import joinedload

from services.backend.models import (
    Organization,
    OrganizationMembership,
    Role,
    User,
)
from services.backend.models.organization import UserRole


@strawberry.type
class RoleType:
    id: strawberry.ID
    name: str
    slug: str
    description: Optional[str]
    scope: str
    created_at: datetime
    updated_at: datetime
    _model_id: strawberry.Private[int]

    @classmethod
    def from_model(cls, model: Role) -> RoleType:
        return cls(
            id=strawberry.ID(str(model.id)),
            name=model.name,
            slug=model.slug,
            description=model.description,
            scope=model.scope,
            created_at=model.created_at,
            updated_at=model.updated_at,
            _model_id=model.id,
        )


@strawberry.type
class UserType:
    id: strawberry.ID
    email: str
    full_name: Optional[str]
    display_name: Optional[str]
    is_active: bool
    last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    _model_id: strawberry.Private[uuid.UUID]

    @classmethod
    def from_model(cls, model: User) -> UserType:
        return cls(
            id=strawberry.ID(str(model.id)),
            email=model.email,
            full_name=model.full_name,
            display_name=model.display_name,
            is_active=model.is_active,
            last_seen_at=model.last_seen_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            _model_id=model.id,
        )


@strawberry.type
class OrganizationMembershipType:
    id: strawberry.ID
    title: Optional[str]
    status: str
    joined_at: Optional[datetime]
    left_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    user: Optional[UserType]
    roles: list[RoleType]
    _model_id: strawberry.Private[int]
    _organization_id: strawberry.Private[uuid.UUID]

    @classmethod
    def from_model(cls, model: OrganizationMembership) -> OrganizationMembershipType:
        user = UserType.from_model(model.user) if model.user else None
        roles = [RoleType.from_model(user_role.role) for user_role in model.roles]
        return cls(
            id=strawberry.ID(str(model.id)),
            title=model.title,
            status=model.status,
            joined_at=model.joined_at,
            left_at=model.left_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            user=user,
            roles=roles,
            _model_id=model.id,
            _organization_id=model.organization_id,
        )


@strawberry.type
class OrganizationType:
    id: strawberry.ID
    name: str
    slug: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    _model_id: strawberry.Private[uuid.UUID]

    @strawberry.field(description="Members belonging to this organization.")
    def members(self, info: Info) -> list[OrganizationMembershipType]:
        session = info.context.session
        memberships = (
            session.query(OrganizationMembership)
            .options(
                joinedload(OrganizationMembership.user),
                joinedload(OrganizationMembership.roles).joinedload(UserRole.role),
            )
            .filter(OrganizationMembership.organization_id == self._model_id)
            .order_by(OrganizationMembership.created_at.asc())
            .all()
        )
        return [OrganizationMembershipType.from_model(m) for m in memberships]

    @strawberry.field(description="Roles defined within this organization context.")
    def roles(self, info: Info) -> list[RoleType]:
        session = info.context.session
        roles = (
            session.query(Role)
            .filter(Role.organization_id == self._model_id)
            .order_by(Role.created_at.asc())
            .all()
        )
        return [RoleType.from_model(role) for role in roles]

    @classmethod
    def from_model(cls, model: Organization) -> OrganizationType:
        return cls(
            id=strawberry.ID(str(model.id)),
            name=model.name,
            slug=model.slug,
            description=model.description,
            status=model.status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            _model_id=model.id,
        )
