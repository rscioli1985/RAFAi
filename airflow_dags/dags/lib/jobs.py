from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import joinedload

from services.backend.models import Job, JobEvent
from services.common.db import session_scope


def build_job_context(job_id: str) -> Dict[str, Any]:
    """Return job + organization metadata shared across tasks."""
    job = _get_job(job_id, eager=True)
    return {
        "job_id": str(job.id),
        "organization_id": str(job.organization_id),
        "owner_user_id": str(job.owner_user_id) if job.owner_user_id else None,
        "priority": job.priority,
        "dag_id": job.dag_id,
    }


def mark_job_running(job_id: str, message: str) -> None:
    _update_job(job_id, status="running", message=message)


def append_job_event(job_id: str, state: str, message: str, airflow_task_id: Optional[str] = None) -> None:
    _update_job(job_id, state_override=state, message=message, airflow_task_id=airflow_task_id, mutate_status=False)


def mark_job_completed(job_id: str, message: str = "Job completed", counts: Optional[Dict[str, Any]] = None) -> None:
    msg = message
    if counts:
        msg = f"{message}. Stats: {counts}"
    _update_job(job_id, status="completed", completed=True, message=msg, state_override="completed")


def mark_job_failed(job_id: str, error: str, airflow_task_id: Optional[str] = None) -> None:
    _update_job(
        job_id,
        status="failed",
        message=error[:2000],
        state_override="failed",
        airflow_task_id=airflow_task_id,
        error=error[:2000],
        completed=True,
    )


def job_failure_callback(context) -> None:
    """Airflow DAG failure hook to sync status into Postgres."""
    dag_run = context.get("dag_run")
    task_instance = context.get("task_instance")
    conf = getattr(dag_run, "conf", {}) or {}
    job_id = conf.get("job_id")
    if not job_id:
        return
    exc = context.get("exception")
    error = repr(exc) if exc else "Unknown DAG failure"
    task_id = getattr(task_instance, "task_id", None)
    mark_job_failed(job_id, error=error, airflow_task_id=task_id)


def _update_job(
    job_id: str,
    *,
    status: Optional[str] = None,
    message: Optional[str] = None,
    airflow_task_id: Optional[str] = None,
    error: Optional[str] = None,
    completed: bool = False,
    state_override: Optional[str] = None,
    mutate_status: bool = True,
) -> None:
    job_uuid = _parse_uuid(job_id)
    with session_scope() as session:
        job = session.query(Job).options(joinedload(Job.events)).filter(Job.id == job_uuid).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if mutate_status and status:
            job.status = status
        if error:
            job.error = error
        if completed:
            job.completed_at = datetime.now(timezone.utc)

        event_state = state_override or status or "info"
        job.events.append(
            JobEvent(
                state=event_state,
                message=message,
                airflow_task_id=airflow_task_id,
            )
        )


def _get_job(job_id: str, *, eager: bool = False) -> Job:
    job_uuid = _parse_uuid(job_id)
    with session_scope() as session:
        query = session.query(Job)
        if eager:
            query = query.options(joinedload(Job.events))
        job = query.filter(Job.id == job_uuid).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        session.expunge(job)
    return job


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid job id: {value}") from exc
