from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass(slots=True)
class GraphQLContext:
    """Per-request dependencies made available to GraphQL resolvers."""

    session: Session
