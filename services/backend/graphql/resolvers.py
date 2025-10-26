from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

import strawberry
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from services.backend.models import Job, JobEvent, Organization, User
from services.backend.orchestration import AirflowClientError
from services.common.metrics import (
    record_job_canceled,
    record_job_failed,
    record_job_submitted,
)

from .types import (
    JobEntityFilter,
    JobFilterInput,
    JobResultType,
    JobStatusEnum,
    JobType,
    OrganizationType,
    RunScrapeInput,
    UserType,
)


def _query_organizations(session: Session) -> List[Organization]:
    return session.query(Organization).order_by(Organization.created_at.asc()).all()


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


def resolve_job(info, id: strawberry.ID) -> Optional[JobType]:
    session: Session = info.context.session
    job_id = _parse_uuid(id)
    if not job_id:
        return None
    job = (
        session.query(Job)
        .options(joinedload(Job.events))
        .filter(Job.id == job_id)
        .first()
    )
    return JobType.from_model(job) if job else None


def resolve_jobs(
    info,
    filter: Optional[JobFilterInput] = None,
    limit: int = 50,
    after: Optional[strawberry.ID] = None,
) -> List[JobType]:
    session: Session = info.context.session
    limit = max(1, min(limit, 200))
    query = session.query(Job).options(joinedload(Job.events)).order_by(Job.created_at.desc(), Job.id.desc())

    if filter:
        if filter.status:
            query = query.filter(Job.status == filter.status.value)
        if filter.job_type:
            query = query.filter(Job.type == filter.job_type.value)
        if filter.owner_id:
            owner_uuid = _parse_uuid(filter.owner_id)
            if owner_uuid:
                query = query.filter(Job.owner_user_id == owner_uuid)
        if filter.organization_id:
            org_uuid = _parse_uuid(filter.organization_id)
            if org_uuid:
                query = query.filter(Job.organization_id == org_uuid)

    if after:
        cursor_uuid = _parse_uuid(after)
        if cursor_uuid:
            cursor = (
                session.query(Job.created_at, Job.id)
                .filter(Job.id == cursor_uuid)
                .first()
            )
            if cursor:
                query = query.filter(
                    or_(
                        Job.created_at < cursor.created_at,
                        and_(Job.created_at == cursor.created_at, Job.id < cursor.id),
                    )
                )

    jobs = query.limit(limit).all()
    return [JobType.from_model(job) for job in jobs]


def resolve_job_results(
    info,
    job_id: strawberry.ID,
    entity: Optional[JobEntityFilter] = None,
) -> Optional[JobResultType]:
    session: Session = info.context.session
    job_uuid = _parse_uuid(job_id)
    if not job_uuid:
        return None
    exists = session.query(Job.id).filter(Job.id == job_uuid).first()
    if not exists:
        return None
    return JobResultType.from_job(job_uuid, entity)


def run_scrape_mutation(info, input: RunScrapeInput) -> JobType:
    if not input.subreddits:
        raise ValueError("At least one subreddit is required")

    session: Session = info.context.session
    airflow_client = info.context.airflow_client
    owner, organization = _resolve_owner(session)
    conf = {
        "subreddits": input.subreddits,
        "keywords": input.keywords or [],
        "depth": input.depth or 100,
        "priority": input.priority or 0,
        "backfill_days": input.backfill_days,
    }

    job = _enqueue_job(
        session=session,
        airflow_client=airflow_client,
        organization_id=organization.id,
        owner_id=owner.id if owner else None,
        job_type="reddit_scrape",
        dag_id="reddit_ingest",
        conf=conf,
        priority=input.priority or 0,
        description="Reddit scrape requested via GraphQL",
    )
    return JobType.from_model(job)


def reanalyze_mutation(info, job_id: strawberry.ID, llm_profile: str) -> JobType:
    session: Session = info.context.session
    airflow_client = info.context.airflow_client
    owner, organization = _resolve_owner(session)
    source_job = _require_job(session, job_id)

    conf = {
        "source_job_id": str(source_job.id),
        "llm_profile": llm_profile,
    }

    job = _enqueue_job(
        session=session,
        airflow_client=airflow_client,
        organization_id=organization.id,
        owner_id=owner.id if owner else None,
        job_type="analysis_reanalyze",
        dag_id="analysis_enrich",
        conf=conf,
        priority=source_job.priority,
        description="Reanalyze posts via GraphQL",
    )
    return JobType.from_model(job)


def reembed_mutation(info, post_ids: List[strawberry.ID], model: str) -> JobType:
    if not post_ids:
        raise ValueError("postIds must not be empty")

    session: Session = info.context.session
    airflow_client = info.context.airflow_client
    owner, organization = _resolve_owner(session)

    conf = {
        "post_ids": [str(pid) for pid in post_ids],
        "model": model,
    }

    job = _enqueue_job(
        session=session,
        airflow_client=airflow_client,
        organization_id=organization.id,
        owner_id=owner.id if owner else None,
        job_type="embedding_generate",
        dag_id="embedding_generate",
        conf=conf,
        priority=0,
        description="Rebuild embeddings via GraphQL",
    )
    return JobType.from_model(job)


def cancel_job_mutation(info, job_id: strawberry.ID) -> JobType:
    session: Session = info.context.session
    job = _require_job(session, job_id)
    job.status = JobStatusEnum.canceled.value
    job.completed_at = datetime.utcnow()
    job.events.append(JobEvent(state="canceled", message="Canceled via GraphQL"))
    record_job_canceled(job.type)
    return JobType.from_model(job)


def _enqueue_job(
    *,
    session: Session,
    airflow_client,
    organization_id: uuid.UUID,
    owner_id: Optional[uuid.UUID],
    job_type: str,
    dag_id: str,
    conf: dict,
    priority: int,
    description: str,
) -> Job:
    job = Job(
        organization_id=organization_id,
        owner_user_id=owner_id,
        type=job_type,
        status=JobStatusEnum.pending.value,
        dag_id=dag_id,
        priority=priority,
        conf=conf,
    )
    session.add(job)
    session.flush()
    job.events.append(JobEvent(state="created", message=description))
    record_job_submitted(job_type)

    payload = {**conf, "job_id": str(job.id)}

    try:
        dag_run_id = airflow_client.trigger_dag_run(dag_id=dag_id, conf=payload)
    except AirflowClientError as exc:
        job.status = JobStatusEnum.failed.value
        job.error = str(exc)
        job.events.append(JobEvent(state="failed", message=str(exc)))
        record_job_failed(job_type)
        raise

    job.status = JobStatusEnum.queued.value
    job.airflow_run_id = dag_run_id
    job.events.append(JobEvent(state="queued", message="DAG triggered", airflow_task_id=dag_run_id))
    return job


def _resolve_owner(session: Session) -> tuple[Optional[User], Organization]:
    organization = session.query(Organization).first()
    if not organization:
        raise ValueError("No organization configured; seed data first")
    user = session.query(User).first()
    return user, organization


def _require_job(session: Session, job_id: strawberry.ID) -> Job:
    job_uuid = _parse_uuid(job_id)
    if not job_uuid:
        raise ValueError("Invalid job id")
    job = (
        session.query(Job)
        .options(joinedload(Job.events))
        .filter(Job.id == job_uuid)
        .first()
    )
    if not job:
        raise ValueError("Job not found")
    return job


def _parse_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None
