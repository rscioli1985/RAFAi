from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session, joinedload

from services.backend.models import Job, JobEvent
from services.backend.orchestration import AirflowClient, AirflowClientError
from services.common.db import session_scope
from services.common.metrics import (
    record_job_canceled,
    record_job_completed,
    record_job_failed,
)


logger = logging.getLogger(__name__)

RUNNING_STATES = {"queued", "running", "up_for_retry", "up_for_reschedule"}
SUCCESS_STATES = {"success"}
FAILED_STATES = {"failed"}
CANCELED_STATES = {"canceled"}


def reconcile_once(airflow: AirflowClient) -> int:
    """Poll Airflow for inflight jobs and sync statuses."""
    with session_scope() as session:
        jobs = _load_target_jobs(session)
        if not jobs:
            return 0
        updated = 0
        for job in jobs:
            if not job.airflow_run_id:
                continue
            try:
                dag_run = airflow.get_dag_run(job.dag_id, job.airflow_run_id)
            except AirflowClientError as exc:
                logger.warning("Failed to fetch dag run for job %s: %s", job.id, exc)
                continue
            new_status, message = _map_state(dag_run.get("state"), dag_run)
            if not new_status or new_status == job.status:
                continue
            _apply_status(job, new_status, message)
            updated += 1
        if updated:
            logger.info("Reconciled %d jobs", updated)
        return updated


def _load_target_jobs(session: Session) -> Iterable[Job]:
    states = ["pending", "queued", "running"]
    return (
        session.query(Job)
        .options(joinedload(Job.events))
        .filter(Job.status.in_(states))
        .all()
    )


def _map_state(state: Optional[str], dag_run: dict) -> tuple[Optional[str], str]:
    state = (state or "").lower()
    if state in RUNNING_STATES:
        return "running", f"Airflow dag_run state={state}"
    if state in SUCCESS_STATES:
        return "completed", "Airflow reported success"
    if state in FAILED_STATES:
        return "failed", dag_run.get("note") or "Airflow reported failure"
    if state in CANCELED_STATES:
        return "canceled", "Airflow reported cancellation"
    return None, ""


def _apply_status(job: Job, new_status: str, message: str) -> None:
    job.status = new_status
    if new_status == "completed":
        job.completed_at = datetime.now(timezone.utc)
        record_job_completed(job.type)
    if new_status == "failed":
        job.error = message
        record_job_failed(job.type)
    if new_status == "canceled":
        record_job_canceled(job.type)
    job.events.append(JobEvent(state=new_status, message=message))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile job status with Airflow DAG run state.")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds (default: 60)")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single reconciliation pass and exit.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    airflow = AirflowClient.from_settings()
    logger.info(
        "Starting Airflow reconciliation worker (interval=%ss, mock_mode=%s)",
        args.interval,
        airflow.mock_mode,
    )

    try:
        while True:
            reconcile_once(airflow)
            if args.once:
                break
            time.sleep(max(args.interval, 5))
    except KeyboardInterrupt:
        logger.info("Reconciliation worker interrupted; exiting.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
