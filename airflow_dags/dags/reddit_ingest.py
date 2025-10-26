from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    from airflow.decorators import dag, task
    from airflow.operators.python import get_current_context
except ImportError:  # pragma: no cover - allows linting without Airflow installed
    raise RuntimeError("Airflow must be installed to load DAGs")

from services.common.db import session_scope
from services.ingestion.persistence import persist_posts
from services.ingestion.reddit_client import RedditClient

from airflow_dags.dags.lib import init_logging, jobs, match_keywords, sanitize_text, to_datetime


logger = logging.getLogger(__name__)
init_logging()


DEFAULT_ARGS = {
    "owner": "nilrag",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


@dag(
    dag_id="reddit_ingest",
    description="Fetch Reddit content and persist into the shared Postgres store.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    on_failure_callback=jobs.job_failure_callback,
    tags=["reddit", "ingestion"],
)
def reddit_ingest():
    @task(task_id="bootstrap_job")
    def bootstrap_job_task() -> Dict[str, Any]:
        context = get_current_context()
        conf = dict((context.get("dag_run").conf or {}))
        job_id = conf.get("job_id")
        if not job_id:
            raise ValueError("job_id missing from DAG conf")

        job_ctx = jobs.build_job_context(job_id)
        job_ctx.update(
            subreddits=conf.get("subreddits") or [],
            keywords=conf.get("keywords") or [],
            depth=int(conf.get("depth") or 100),
            backfill_days=conf.get("backfill_days"),
        )
        if not job_ctx["subreddits"]:
            raise ValueError("subreddits list is required")

        jobs.mark_job_running(job_id, "reddit_ingest DAG started")
        logger.info("Bootstrapped job %s with conf %s", job_id, {k: v for k, v in job_ctx.items() if k != "keywords"})
        return job_ctx

    @task(task_id="fetch_posts")
    def fetch_posts_task(job_ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        reddit = RedditClient()
        max_per_sub = job_ctx["depth"]
        keywords = [kw.lower() for kw in job_ctx["keywords"] if kw]
        collected: List[Dict[str, Any]] = []

        for subreddit in job_ctx["subreddits"]:
            posts = reddit.fetch_new_posts(subreddit, limit=max_per_sub)
            for post in posts:
                if keywords and not match_keywords(post, keywords):
                    continue
                collected.append(
                    {
                        "external_id": post["id"],
                        "subreddit": post["subreddit"],
                        "author": sanitize_text(post.get("author")),
                        "title": sanitize_text(post.get("title")),
                        "body": sanitize_text(post.get("body")),
                        "url": post.get("url"),
                        "score": post.get("score"),
                        "posted_at": to_datetime(post.get("created_utc")),
                    }
                )
        jobs.append_job_event(job_ctx["job_id"], state="fetch_posts", message=f"Fetched {len(collected)} posts")
        return collected

    @task(task_id="persist_posts")
    def persist_posts_task(job_ctx: Dict[str, Any], posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        job_uuid = uuid.UUID(job_ctx["job_id"])
        org_uuid = uuid.UUID(job_ctx["organization_id"])
        inserted = 0

        with session_scope() as session:
            inserted = persist_posts(
                session,
                job_id=job_uuid,
                organization_id=org_uuid,
                posts=posts,
            )
            jobs.append_job_event(
                job_ctx["job_id"], state="persist_posts", message=f"Inserted {inserted} posts", airflow_task_id="persist_posts"
            )
        return {"inserted": inserted, "received": len(posts)}

    @task(task_id="finalize_job")
    def finalize_job_task(job_ctx: Dict[str, Any], stats: Dict[str, Any]) -> None:
        jobs.mark_job_completed(
            job_ctx["job_id"],
            message="reddit_ingest DAG completed",
            counts=stats,
        )

    ctx = bootstrap_job_task()
    stored = persist_posts_task(ctx, fetch_posts_task(ctx))
    finalize_job_task(ctx, stored)


reddit_ingest()
