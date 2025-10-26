from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    from airflow.decorators import dag, task
    from airflow.operators.python import get_current_context
except ImportError:  # pragma: no cover
    raise RuntimeError("Airflow must be installed to load DAGs")

from services.backend.models import Analysis, Post
from services.common.config import settings
from services.common.db import session_scope
from services.ingestion.persistence import persist_analysis

from airflow_dags.dags.lib import init_logging, jobs, sanitize_text
from services.common import metrics


logger = logging.getLogger(__name__)
init_logging()


DEFAULT_ARGS = {
    "owner": "nilrag",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="analysis_enrich",
    description="Perform lightweight LLM-style summaries for Reddit posts tied to a job.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    on_failure_callback=jobs.job_failure_callback,
    tags=["analysis", "llm"],
)
def analysis_enrich():
    @task(task_id="bootstrap_job")
    def bootstrap_job_task() -> Dict[str, Any]:
        context = get_current_context()
        conf = dict((context.get("dag_run").conf or {}))
        job_id = conf.get("job_id")
        source_job_id = conf.get("source_job_id")
        if not job_id or not source_job_id:
            raise ValueError("job_id and source_job_id are required")

        job_ctx = jobs.build_job_context(job_id)
        job_ctx.update(
            source_job_id=source_job_id,
            llm_profile=conf.get("llm_profile", "default"),
            max_items=int(conf.get("max_items") or 50),
        )

        jobs.mark_job_running(job_id, "analysis_enrich DAG started")
        return job_ctx

    @task(task_id="load_posts")
    def load_posts_task(job_ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_uuid = uuid.UUID(job_ctx["source_job_id"])
        rows: List[Dict[str, Any]] = []

        with session_scope() as session:
            query = (
                session.query(Post)
                .filter(Post.job_id == source_uuid)
                .order_by(Post.created_at.desc())
                .limit(job_ctx["max_items"])
            )
            for post in query.all():
                rows.append(
                    {
                        "post_id": post.id,
                        "title": sanitize_text(post.title),
                        "body": sanitize_text(post.body),
                        "score": post.score or 0,
                        "subreddit": post.subreddit,
                    }
                )

        jobs.append_job_event(job_ctx["job_id"], "load_posts", f"Loaded {len(rows)} posts from source job")
        if not rows:
            logger.warning("No posts found for source_job_id=%s", job_ctx["source_job_id"])
        return rows

    @task(task_id="run_llm_analysis")
    def run_llm_analysis_task(job_ctx: Dict[str, Any], posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        analyses: List[Dict[str, Any]] = []
        total_tokens = 0
        for post in posts:
            summary = _summarize_text(post["title"], post["body"])
            sentiment = _estimate_sentiment(post["body"])
            total_tokens += _estimate_tokens(post["title"], post["body"])
            analyses.append(
                {
                    "post_id": post["post_id"],
                    "model": settings.llm_model,
                    "summary": summary,
                    "sentiment": sentiment,
                    "metadata_json": {
                        "subreddit": post["subreddit"],
                        "score": post["score"],
                        "profile": job_ctx["llm_profile"],
                    },
                }
            )
        jobs.append_job_event(job_ctx["job_id"], "analysis_run", f"Prepared {len(analyses)} analyses")
        metrics.record_llm_tokens(settings.llm_model, total_tokens)
        return analyses

    @task(task_id="persist_analyses")
    def persist_analyses_task(job_ctx: Dict[str, Any], analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        job_uuid = uuid.UUID(job_ctx["job_id"])
        inserted = 0

        with session_scope() as session:
            inserted = persist_analysis(
                session,
                job_id=job_uuid,
                records=analyses,
            )
        jobs.append_job_event(job_ctx["job_id"], "persist_analyses", f"Inserted {inserted} analysis rows")
        return {"inserted": inserted}

    @task(task_id="finalize_job")
    def finalize_job_task(job_ctx: Dict[str, Any], stats: Dict[str, Any]) -> None:
        jobs.mark_job_completed(
            job_ctx["job_id"],
            message="analysis_enrich DAG completed",
            counts=stats,
        )

    ctx = bootstrap_job_task()
    analyses = run_llm_analysis_task(ctx, load_posts_task(ctx))
    stats = persist_analyses_task(ctx, analyses)
    finalize_job_task(ctx, stats)


analysis_enrich()


def _summarize_text(title: str, body: str, limit: int = 256) -> str:
    clean_title = sanitize_text(title)
    clean_body = sanitize_text(body)
    base = f"{clean_title.strip()} - {clean_body.strip()}"
    if len(base) <= limit:
        return base
    return f"{base[:limit].rstrip()}..."


def _estimate_sentiment(body: str) -> str:
    clean_body = sanitize_text(body)
    if not clean_body:
        return "neutral"
    tokens = [tok.lower() for tok in clean_body.split()]
    positive = sum(1 for tok in tokens if tok in {"good", "great", "love", "ship", "win"})
    negative = sum(1 for tok in tokens if tok in {"bad", "hate", "angry", "fail", "bug"})
    if positive == negative:
        return "neutral"
    return "positive" if positive > negative else "negative"


def _estimate_tokens(title: str, body: str) -> int:
    clean_title = sanitize_text(title)
    clean_body = sanitize_text(body)
    return max(1, len(clean_title.split()) + len(clean_body.split()))
