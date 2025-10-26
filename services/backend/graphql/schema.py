from __future__ import annotations

import strawberry
from strawberry.types import Info

try:  # pragma: no cover - optional for schema import during tests
    from fastapi import APIRouter, Depends  # type: ignore
    from strawberry.fastapi import GraphQLRouter  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None  # type: ignore
    GraphQLRouter = None  # type: ignore
    Depends = None  # type: ignore

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


if Depends is not None:

    async def get_graphql_context(session=Depends(get_session)) -> GraphQLContext:  # type: ignore[misc]
        return GraphQLContext(session=session, airflow_client=airflow_client)

else:  # pragma: no cover

    async def get_graphql_context(session) -> GraphQLContext:
        if session is None:
            raise RuntimeError("FastAPI dependency injection unavailable; pass a session explicitly.")
        return GraphQLContext(session=session, airflow_client=airflow_client)


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
