from __future__ import annotations

import strawberry
from strawberry.types import Info

try:  # pragma: no cover - optional for schema import during tests
    from fastapi import APIRouter, Depends, HTTPException, Request, status  # type: ignore
    from strawberry.fastapi import GraphQLRouter  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None  # type: ignore
    GraphQLRouter = None  # type: ignore
    Depends = None  # type: ignore
    HTTPException = None  # type: ignore
    Request = None  # type: ignore
    status = None  # type: ignore

import uuid

from services.backend.models import Organization, OrganizationMembership, User

from services.backend.orchestration import AirflowClient
from services.common.db import get_session
from .context import GraphQLContext
from .resolvers import (
    cancel_job_mutation,
    reanalyze_mutation,
    reembed_mutation,
    resolve_job,
    resolve_job_results,
    resolve_jobs,
    resolve_organization_by_slug,
    resolve_organizations,
    resolve_viewer,
    run_scrape_mutation,
)
from .types import JobResultType, JobType, OrganizationType, UserType


airflow_client = AirflowClient.from_settings()


def _authenticate_request(request: Request, session) -> tuple[User | None, Organization | None]:
    user_header = request.headers.get("X-User-ID")
    org_header = request.headers.get("X-Org-ID")
    if not user_header or not org_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth headers")
    try:
        user_uuid = uuid.UUID(user_header)
        org_uuid = uuid.UUID(org_header)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid auth headers")

    user = session.get(User, user_uuid)
    org = session.get(Organization, org_uuid)
    if not user or not org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user/org")

    membership = (
        session.query(OrganizationMembership)
        .filter(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.status == "active",
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not part of organization")
    return user, org


if Depends is not None:

    async def get_graphql_context(request: Request, session=Depends(get_session)) -> GraphQLContext:  # type: ignore[misc]
        user, org = _authenticate_request(request, session)
        return GraphQLContext(session=session, airflow_client=airflow_client, user=user, organization=org)

else:  # pragma: no cover

    async def get_graphql_context(session) -> GraphQLContext:
        if session is None:
            raise RuntimeError("FastAPI dependency injection unavailable; pass a session explicitly.")
        return GraphQLContext(session=session, airflow_client=airflow_client, user=None, organization=None)


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

    job: JobType | None = strawberry.field(resolver=resolve_job, description="Fetch a single job by id.")
    jobs: list[JobType] = strawberry.field(
        resolver=resolve_jobs,
        description="List jobs with optional filters, cursor pagination (after) and limit.",
    )
    job_results: JobResultType | None = strawberry.field(
        resolver=resolve_job_results, description="Fetch persisted outputs tied to a job."
    )


@strawberry.type
class Mutation:
    run_scrape: JobType = strawberry.mutation(resolver=run_scrape_mutation)
    reanalyze: JobType = strawberry.mutation(resolver=reanalyze_mutation)
    reembed: JobType = strawberry.mutation(resolver=reembed_mutation)
    cancel_job: JobType = strawberry.mutation(resolver=cancel_job_mutation)


schema = strawberry.Schema(query=Query, mutation=Mutation)

if GraphQLRouter is not None:  # pragma: no cover
    graphql_router: APIRouter | None = GraphQLRouter(
        schema,
        context_getter=get_graphql_context,
        graphiql=True,
    )
else:
    graphql_router = None
