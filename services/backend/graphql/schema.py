from __future__ import annotations

from fastapi import APIRouter, Depends
import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.types import Info

from services.common.db import get_session
from .context import GraphQLContext
from .resolvers import (
    resolve_organization_by_slug,
    resolve_organizations,
    resolve_viewer,
)
from .types import OrganizationType, UserType


async def get_graphql_context(session=Depends(get_session)) -> GraphQLContext:
    return GraphQLContext(session=session)


@strawberry.type
class Query:
    viewer: UserType | None = strawberry.field(resolver=resolve_viewer)
    organizations: list[OrganizationType] = strawberry.field(
        resolver=resolve_organizations,
        description="List all organizations current user can access (placeholder impl).",
    )

    @strawberry.field(description="Look up a single organization by slug.")
    def organization_by_slug(self, info: Info, slug: str) -> OrganizationType | None:
        return resolve_organization_by_slug(slug=slug, info=info)


schema = strawberry.Schema(query=Query)
graphql_router: APIRouter = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
    graphiql=True,
)
