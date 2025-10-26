from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import strawberry
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from services.backend.models import Job, JobEvent, Organization, User
from services.backend.orchestration import AirflowClientError
from services.common.config import settings
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
    viewer_org = _get_viewer_org(session)
    job_id = _parse_uuid(id)
    if not job_id:
        return None
    job = (
        session.query(Job)
        .options(joinedload(Job.events))
        .filter(Job.id == job_id, Job.organization_id == viewer_org.id)
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

    viewer_org = _get_viewer_org(session)

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

    query = query.filter(Job.organization_id == viewer_org.id)

    jobs = query.limit(limit).all()
    return [JobType.from_model(job) for job in jobs]


def resolve_job_results(
    info,
    job_id: strawberry.ID,
    entity: Optional[JobEntityFilter] = None,
) -> Optional[JobResultType]:
    session: Session = info.context.session
    viewer_org = _get_viewer_org(session)
    job_uuid = _parse_uuid(job_id)
    if not job_uuid:
        return None
    exists = (
        session.query(Job.id)
        .filter(Job.id == job_uuid, Job.organization_id == viewer_org.id)
        .first()
    )
    if not exists:
        return None
    return JobResultType.from_job(job_uuid, entity)


def run_scrape_mutation(info, input: RunScrapeInput) -> JobType:
    if not input.subreddits:
        raise ValueError("At least one subreddit is required")
    if not settings.feature_run_scrape:
        raise ValueError("runScrape feature is disabled")
    _enforce_scrape_limits(input)

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
        cost_estimate_cents=None,
    )
    return JobType.from_model(job)


def reanalyze_mutation(info, job_id: strawberry.ID, llm_profile: str) -> JobType:
    if not settings.feature_reanalyze:
        raise ValueError("reanalyze feature is disabled")
    session: Session = info.context.session
    airflow_client = info.context.airflow_client
    owner, organization = _resolve_owner(session)
    source_job = _require_job(session, job_id)

    conf = {
        "source_job_id": str(source_job.id),
        "llm_profile": llm_profile,
    }

    estimated_cost = _estimate_job_cost("analysis_reanalyze")
    _ensure_llm_budget(session, organization.id, estimated_cost)

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
        cost_estimate_cents=estimated_cost,
    )
    return JobType.from_model(job)


def reembed_mutation(info, post_ids: List[strawberry.ID], model: str) -> JobType:
    if not post_ids:
        raise ValueError("postIds must not be empty")
    if not settings.feature_reembed:
        raise ValueError("reembed feature is disabled")

    session: Session = info.context.session
    airflow_client = info.context.airflow_client
    owner, organization = _resolve_owner(session)

    conf = {
        "post_ids": [str(pid) for pid in post_ids],
        "model": model,
    }

    estimated_cost = _estimate_job_cost("embedding_generate")
    _ensure_llm_budget(session, organization.id, estimated_cost)

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
        cost_estimate_cents=estimated_cost,
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
    cost_estimate_cents: Optional[int],
) -> Job:
    job = Job(
        organization_id=organization_id,
        owner_user_id=owner_id,
        type=job_type,
        status=JobStatusEnum.pending.value,
        dag_id=dag_id,
        priority=priority,
        conf=conf,
        cost_estimate_cents=cost_estimate_cents,
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
    organization = _get_viewer_org(session)
    user = session.query(User).first()
    return user, organization


def _get_viewer_org(session: Session) -> Organization:
    organization = session.query(Organization).first()
    if not organization:
        raise ValueError("No organization configured; seed data first")
    return organization


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


def _enforce_scrape_limits(input: RunScrapeInput) -> None:
    max_subreddits = max(1, settings.max_subreddits_per_job)
    max_keywords = max(1, settings.max_keywords_per_job)
    if len(input.subreddits) > max_subreddits:
        raise ValueError(f"Too many subreddits; max allowed is {max_subreddits}.")
    keyword_count = len(input.keywords or [])
    if keyword_count > max_keywords:
        raise ValueError(f"Too many keywords; max allowed is {max_keywords}.")


LLM_JOB_TYPES = {"analysis_reanalyze", "embedding_generate"}
LLM_COST_ESTIMATE_CENTS = {
    "analysis_reanalyze": 200,
    "embedding_generate": 150,
}


def _estimate_job_cost(job_type: str) -> Optional[int]:
    return LLM_COST_ESTIMATE_CENTS.get(job_type)


def _ensure_llm_budget(session: Session, organization_id: uuid.UUID, estimated_cost: Optional[int]) -> None:
    if not estimated_cost or estimated_cost <= 0:
        return
    budget = settings.llm_daily_budget_cents
    if budget <= 0:
        return
    window_start = datetime.utcnow() - timedelta(hours=24)
    spent = (
        session.query(func.coalesce(func.sum(Job.cost_estimate_cents), 0))
        .filter(
            Job.organization_id == organization_id,
            Job.type.in_(LLM_JOB_TYPES),
            Job.created_at >= window_start,
            Job.status != JobStatusEnum.canceled.value,
        )
        .scalar()
    )
    if spent + estimated_cost > budget:
        raise ValueError("LLM daily budget exceeded. Try again later or contact support.")
