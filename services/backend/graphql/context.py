from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.backend.models import Organization, User
from services.backend.orchestration import AirflowClient


@dataclass(slots=True)
class GraphQLContext:
    """Per-request dependencies made available to GraphQL resolvers."""

    session: Session
    airflow_client: AirflowClient
    user: User | None
    organization: Organization | None
