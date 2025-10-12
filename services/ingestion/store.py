from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session


metadata = sa.MetaData()

raw_posts = sa.Table(
    "raw_posts",
    metadata,
    sa.Column("id", sa.String(32), primary_key=True),
    sa.Column("subreddit", sa.String(255), nullable=False, index=True),
    sa.Column("author", sa.String(255)),
    sa.Column("title", sa.Text()),
    sa.Column("body", sa.Text()),
    sa.Column("score", sa.Integer()),
    sa.Column("url", sa.Text()),
    sa.Column("created_utc", sa.DateTime(timezone=True)),
    sa.Column("fetched_at", sa.DateTime(timezone=True)),
    sa.Column("metadata", sa.dialects.postgresql.JSONB),
)

faqs = sa.Table(
    "faqs",
    metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
    sa.Column("question", sa.Text(), nullable=False),
    sa.Column("answer", sa.Text()),
    sa.Column("source_post_id", sa.String(32)),
    sa.Column("created_utc", sa.DateTime(timezone=True)),
    sa.Column("updated_at", sa.DateTime(timezone=True)),
    sa.Column("tags", sa.ARRAY(sa.String(64)), server_default=sa.text("'{}'"), nullable=False),
    sa.Column("confidence", sa.Numeric(5, 2)),
    sa.Column("metadata", sa.dialects.postgresql.JSONB),
)

ingestion_runs = sa.Table(
    "ingestion_runs",
    metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
    sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("status", sa.String(32)),
    sa.Column("error", sa.Text()),
    sa.Column("counts", sa.dialects.postgresql.JSONB),
)


def _existing_ids(session: Session, table: sa.Table, ids: Sequence[str]) -> set[str]:
    if not ids:
        return set()
    rows = session.execute(sa.select(table.c.id).where(table.c.id.in_(list(ids)))).scalars().all()
    return set(rows)


def upsert_raw_posts(session: Session, items: Sequence[Dict[str, Any]]) -> Tuple[int, int]:
    """Insert posts; ignore duplicates by primary key.

    Returns: (inserted_count, total_count)
    """
    if not items:
        return 0, 0
    ids = [it["id"] for it in items]
    existing = _existing_ids(session, raw_posts, ids)
    to_insert = [it for it in items if it["id"] not in existing]
    if to_insert:
        stmt = pg_insert(raw_posts).values(to_insert).on_conflict_do_nothing(index_elements=[raw_posts.c.id])
        session.execute(stmt)
    return len(to_insert), len(items)


def upsert_faqs(session: Session, items: Sequence[Dict[str, Any]]) -> Tuple[int, int]:
    """Insert FAQs if a record with same (source_post_id, question) does not exist.

    Returns: (inserted_count, total_count)
    """
    if not items:
        return 0, 0
    inserted = 0
    for it in items:
        # Check existence
        q = sa.select(faqs.c.id).where(
            sa.and_(
                (faqs.c.source_post_id == it.get("source_post_id")),
                (faqs.c.question == it.get("question")),
            )
        ).limit(1)
        exists = session.execute(q).first()
        if exists:
            continue
        session.execute(sa.insert(faqs).values(**it))
        inserted += 1
    return inserted, len(items)


def record_ingestion_run(
    session: Session,
    *,
    started_at: dt.datetime,
    finished_at: dt.datetime,
    status: str,
    counts: Dict[str, Any],
    error: str | None = None,
) -> int:
    res = session.execute(
        sa.insert(ingestion_runs).values(
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            error=error,
            counts=counts,
        ).returning(ingestion_runs.c.id)
    )
    run_id = int(res.scalar_one())
    return run_id

