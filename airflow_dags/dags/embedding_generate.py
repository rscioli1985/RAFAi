from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np

try:
    from airflow.decorators import dag, task
    from airflow.operators.python import get_current_context
except ImportError:  # pragma: no cover
    raise RuntimeError("Airflow must be installed to load DAGs")

from services.backend.models import Analysis, Embedding
from services.common.config import settings
from services.common.db import session_scope

from airflow_dags.dags.lib import init_logging, jobs


logger = logging.getLogger(__name__)
init_logging()


DEFAULT_ARGS = {
    "owner": "nilrag",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


@dag(
    dag_id="embedding_generate",
    description="Generate embeddings for analyses using a deterministic local encoder.",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    on_failure_callback=jobs.job_failure_callback,
    tags=["embeddings", "vector"],
)
def embedding_generate():
    @task(task_id="bootstrap_job")
    def bootstrap_job_task() -> Dict[str, Any]:
        context = get_current_context()
        conf = dict((context.get("dag_run").conf or {}))
        job_id = conf.get("job_id")
        post_ids = conf.get("post_ids") or []
        if not job_id or not post_ids:
            raise ValueError("job_id and post_ids are required")

        job_ctx = jobs.build_job_context(job_id)
        job_ctx.update(
            post_ids=[int(pid) for pid in post_ids],
            model=conf.get("model", settings.embedding_model),
        )
        jobs.mark_job_running(job_id, "embedding_generate DAG started")
        return job_ctx

    @task(task_id="load_analyses")
    def load_analyses_task(job_ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        with session_scope() as session:
            query = (
                session.query(Analysis)
                .filter(Analysis.post_id.in_(job_ctx["post_ids"]))
                .order_by(Analysis.post_id.asc(), Analysis.created_at.desc())
            )
            for analysis in query.all():
                rows.append(
                    {
                        "analysis_id": analysis.id,
                        "post_id": analysis.post_id,
                        "summary": analysis.summary or "",
                        "model": job_ctx["model"],
                    }
                )
        if not rows:
            logger.warning("No analyses found for post ids %s", job_ctx["post_ids"])
        jobs.append_job_event(job_ctx["job_id"], "load_analyses", f"Loaded {len(rows)} analyses for embeddings")
        return rows

    @task(task_id="encode_vectors")
    def encode_vectors_task(job_ctx: Dict[str, Any], analyses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        vectors: List[Dict[str, Any]] = []
        dim = settings.vector_dim
        for item in analyses:
            vector = _deterministic_embedding(item["summary"], dim)
            vectors.append(
                {
                    "analysis_id": item["analysis_id"],
                    "vector": vector,
                    "dims": dim,
                    "model": job_ctx["model"],
                }
            )
        jobs.append_job_event(job_ctx["job_id"], "encode_vectors", f"Encoded {len(vectors)} embeddings")
        return vectors

    @task(task_id="persist_embeddings")
    def persist_embeddings_task(job_ctx: Dict[str, Any], embeddings: List[Dict[str, Any]]) -> Dict[str, Any]:
        job_uuid = uuid.UUID(job_ctx["job_id"])
        inserted = 0
        with session_scope() as session:
            for record in embeddings:
                session.add(
                    Embedding(
                        job_id=job_uuid,
                        analysis_id=record["analysis_id"],
                        model=record["model"],
                        vector=record["vector"],
                        dims=record["dims"],
                    )
                )
                inserted += 1
        jobs.append_job_event(job_ctx["job_id"], "persist_embeddings", f"Stored {inserted} embedding rows")
        return {"inserted": inserted}

    @task(task_id="finalize_job")
    def finalize_job_task(job_ctx: Dict[str, Any], stats: Dict[str, Any]) -> None:
        jobs.mark_job_completed(
            job_ctx["job_id"],
            message="embedding_generate DAG completed",
            counts=stats,
        )

    ctx = bootstrap_job_task()
    stats = persist_embeddings_task(ctx, encode_vectors_task(ctx, load_analyses_task(ctx)))
    finalize_job_task(ctx, stats)


embedding_generate()


def _deterministic_embedding(text: str, dims: int) -> List[float]:
    seed = abs(hash(text)) % (2**32)
    rng = np.random.default_rng(seed)
    vector = rng.standard_normal(dims)
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()
