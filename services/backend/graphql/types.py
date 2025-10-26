from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

import strawberry
from strawberry import Private
from strawberry.scalars import JSON
from strawberry.types import Info
from sqlalchemy.orm import joinedload, Session

from services.backend.models import (
    Analysis as AnalysisModel,
    Comment as CommentModel,
    Embedding as EmbeddingModel,
    Job as JobModel,
    JobEvent as JobEventModel,
    Organization,
    OrganizationMembership,
    Post as PostModel,
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
    _model_id: Private[int]

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
    _model_id: Private[uuid.UUID]

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
    roles: List[RoleType]
    _model_id: Private[int]
    _organization_id: Private[uuid.UUID]

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
    _model_id: Private[uuid.UUID]

    @strawberry.field(description="Members belonging to this organization.")
    def members(self, info: Info) -> List[OrganizationMembershipType]:
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
    def roles(self, info: Info) -> List[RoleType]:
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


@strawberry.enum
class JobStatusEnum(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


@strawberry.enum
class JobKindEnum(str, Enum):
    reddit_scrape = "reddit_scrape"
    analysis_reanalyze = "analysis_reanalyze"
    embedding_generate = "embedding_generate"


@strawberry.enum
class JobEntityFilter(str, Enum):
    all = "all"
    posts = "posts"
    comments = "comments"
    analyses = "analyses"
    embeddings = "embeddings"


@strawberry.type
class JobEventType:
    state: str
    message: Optional[str]
    airflow_task_id: Optional[str]
    occurred_at: datetime

    @classmethod
    def from_model(cls, model: JobEventModel) -> "JobEventType":
        return cls(
            state=model.state,
            message=model.message,
            airflow_task_id=model.airflow_task_id,
            occurred_at=model.occurred_at,
        )


@strawberry.type
class JobType:
    id: strawberry.ID
    type: JobKindEnum
    status: JobStatusEnum
    dag_id: str
    airflow_run_id: Optional[str]
    priority: int
    conf: JSON
    error: Optional[str]
    cost_estimate_cents: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    events: List[JobEventType]
    _organization_id: Private[uuid.UUID]
    _owner_user_id: Private[Optional[uuid.UUID]]

    @classmethod
    def from_model(cls, model: JobModel) -> "JobType":
        try:
            job_type = JobKindEnum(model.type)
        except ValueError:
            job_type = JobKindEnum.reddit_scrape

        try:
            job_status = JobStatusEnum(model.status)
        except ValueError:
            job_status = JobStatusEnum.pending

        return cls(
            id=strawberry.ID(str(model.id)),
            type=job_type,
            status=job_status,
            dag_id=model.dag_id,
            airflow_run_id=model.airflow_run_id,
            priority=model.priority,
            conf=model.conf,
            error=model.error,
            cost_estimate_cents=model.cost_estimate_cents,
            created_at=model.created_at,
            updated_at=model.updated_at,
            completed_at=model.completed_at,
            events=[JobEventType.from_model(event) for event in model.events],
            _organization_id=model.organization_id,
            _owner_user_id=model.owner_user_id,
        )

    @strawberry.field
    def organization(self, info: Info) -> Optional[OrganizationType]:
        session: Session = info.context.session
        org = session.get(Organization, self._organization_id)
        return OrganizationType.from_model(org) if org else None

    @strawberry.field
    def owner(self, info: Info) -> Optional[UserType]:
        if not self._owner_user_id:
            return None
        session: Session = info.context.session
        user = session.get(User, self._owner_user_id)
        return UserType.from_model(user) if user else None


@strawberry.type
class PostType:
    id: strawberry.ID
    external_id: str
    subreddit: str
    author: Optional[str]
    title: Optional[str]
    body: Optional[str]
    url: Optional[str]
    posted_at: Optional[datetime]
    score: Optional[int]
    metadata: Optional[JSON]

    @classmethod
    def from_model(cls, model: PostModel) -> "PostType":
        return cls(
            id=strawberry.ID(str(model.id)),
            external_id=model.external_id,
            subreddit=model.subreddit,
            author=model.author,
            title=model.title,
            body=model.body,
            url=model.url,
            posted_at=model.posted_at,
            score=model.score,
            metadata=model.metadata_json,
        )


@strawberry.type
class CommentType:
    id: strawberry.ID
    external_id: str
    author: Optional[str]
    body: Optional[str]
    posted_at: Optional[datetime]
    score: Optional[int]
    metadata: Optional[JSON]

    @classmethod
    def from_model(cls, model: CommentModel) -> "CommentType":
        return cls(
            id=strawberry.ID(str(model.id)),
            external_id=model.external_id,
            author=model.author,
            body=model.body,
            posted_at=model.posted_at,
            score=model.score,
            metadata=model.metadata_json,
        )


@strawberry.type
class AnalysisType:
    id: strawberry.ID
    model: str
    summary: Optional[str]
    sentiment: Optional[str]
    metadata: Optional[JSON]

    @classmethod
    def from_model(cls, model: AnalysisModel) -> "AnalysisType":
        return cls(
            id=strawberry.ID(str(model.id)),
            model=model.model,
            summary=model.summary,
            sentiment=model.sentiment,
            metadata=model.metadata_json,
        )


@strawberry.type
class EmbeddingType:
    id: strawberry.ID
    model: str
    vector: List[float]
    dims: int
    score: Optional[float]

    @classmethod
    def from_model(cls, model: EmbeddingModel) -> "EmbeddingType":
        vector_data = list(model.vector) if model.vector is not None else []
        return cls(
            id=strawberry.ID(str(model.id)),
            model=model.model,
            vector=vector_data,
            dims=model.dims,
            score=float(model.score) if model.score is not None else None,
        )


@strawberry.type
class JobResultType:
    job_id: strawberry.ID
    _job_uuid: Private[uuid.UUID]
    _entity_filter: Private[Optional[JobEntityFilter]]

    @classmethod
    def from_job(cls, job_id: uuid.UUID, entity: Optional[JobEntityFilter]) -> "JobResultType":
        return cls(job_id=strawberry.ID(str(job_id)), _job_uuid=job_id, _entity_filter=entity)

    def _allow(self, target: JobEntityFilter) -> bool:
        return (self._entity_filter is None) or (self._entity_filter in {JobEntityFilter.all, target})

    @strawberry.field
    def posts(self, info: Info) -> List[PostType]:
        if not self._allow(JobEntityFilter.posts):
            return []
        session: Session = info.context.session
        posts = (
            session.query(PostModel)
            .filter(PostModel.job_id == self._job_uuid)
            .order_by(PostModel.created_at.asc())
            .all()
        )
        return [PostType.from_model(post) for post in posts]

    @strawberry.field
    def comments(self, info: Info) -> List[CommentType]:
        if not self._allow(JobEntityFilter.comments):
            return []
        session: Session = info.context.session
        comments = (
            session.query(CommentModel)
            .filter(CommentModel.job_id == self._job_uuid)
            .order_by(CommentModel.created_at.asc())
            .all()
        )
        return [CommentType.from_model(comment) for comment in comments]

    @strawberry.field
    def analyses(self, info: Info) -> List[AnalysisType]:
        if not self._allow(JobEntityFilter.analyses):
            return []
        session: Session = info.context.session
        analyses = (
            session.query(AnalysisModel)
            .filter(AnalysisModel.job_id == self._job_uuid)
            .order_by(AnalysisModel.created_at.asc())
            .all()
        )
        return [AnalysisType.from_model(analysis) for analysis in analyses]

    @strawberry.field
    def embeddings(self, info: Info) -> List[EmbeddingType]:
        if not self._allow(JobEntityFilter.embeddings):
            return []
        session: Session = info.context.session
        embeddings = (
            session.query(EmbeddingModel)
            .filter(EmbeddingModel.job_id == self._job_uuid)
            .order_by(EmbeddingModel.created_at.asc())
            .all()
        )
        return [EmbeddingType.from_model(embedding) for embedding in embeddings]


@strawberry.input
class RunScrapeInput:
    subreddits: List[str]
    keywords: Optional[List[str]] = None
    depth: Optional[int] = 100
    priority: Optional[int] = 0
    backfill_days: Optional[int] = None


@strawberry.input
class JobFilterInput:
    status: Optional[JobStatusEnum] = None
    owner_id: Optional[strawberry.ID] = None
    job_type: Optional[JobKindEnum] = None
    organization_id: Optional[strawberry.ID] = None
