from __future__ import annotations

import logging
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST, Counter, CollectorRegistry, Gauge, generate_latest

logger = logging.getLogger(__name__)

registry = CollectorRegistry()

jobs_submitted = Counter(
    "jobs_submitted_total",
    "Total number of jobs submitted via GraphQL",
    ["job_type"],
    registry=registry,
)
jobs_completed = Counter(
    "jobs_completed_total",
    "Total number of jobs completed (Airflow success)",
    ["job_type"],
    registry=registry,
)
jobs_failed = Counter(
    "jobs_failed_total",
    "Total number of jobs failed (Airflow failure)",
    ["job_type"],
    registry=registry,
)
jobs_canceled = Counter(
    "jobs_canceled_total",
    "Total number of jobs canceled via API or reconciliation",
    ["job_type"],
    registry=registry,
)
reddit_rate_limit_hits = Counter(
    "reddit_rate_limit_hits_total",
    "Number of times Reddit API rate limit was hit.",
    ["subreddit"],
    registry=registry,
)
llm_tokens_consumed = Counter(
    "llm_tokens_consumed_total",
    "Total LLM tokens consumed by enrichment jobs.",
    ["model"],
    registry=registry,
)


def _label(job_type: Optional[str]) -> str:
    return job_type or "unknown"


def record_job_submitted(job_type: Optional[str]) -> None:
    jobs_submitted.labels(job_type=_label(job_type)).inc()


def record_job_completed(job_type: Optional[str]) -> None:
    jobs_completed.labels(job_type=_label(job_type)).inc()


def record_job_failed(job_type: Optional[str]) -> None:
    jobs_failed.labels(job_type=_label(job_type)).inc()


def record_job_canceled(job_type: Optional[str]) -> None:
    jobs_canceled.labels(job_type=_label(job_type)).inc()


def record_reddit_rate_limit_hit(subreddit: Optional[str]) -> None:
    reddit_rate_limit_hits.labels(subreddit=subreddit or "unknown").inc()


def record_llm_tokens(model: Optional[str], tokens: int) -> None:
    if tokens <= 0:
        return
    llm_tokens_consumed.labels(model=model or "unknown").inc(tokens)


def render_prometheus_metrics() -> tuple[bytes, str]:
    """Return (payload, content_type) for FastAPI responses."""
    output = generate_latest(registry)
    return output, CONTENT_TYPE_LATEST
