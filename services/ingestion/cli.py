from __future__ import annotations

import argparse
import datetime as dt
import logging
from typing import Optional

import time
from datetime import timezone

from services.common.config import settings
from services.common.logging import setup_logging
from services.common.db import session_scope
from .reddit_client import RedditClient
from .filters import is_nil_relevant
from .faq_curator import extract_faqs
from .store import upsert_raw_posts, upsert_faqs, record_ingestion_run


setup_logging()
logger = logging.getLogger(__name__)


def _parse_subreddits(raw: str) -> list[str]:
    # Accept + , ; or whitespace separated
    import re

    parts = re.split(r"[+,;\s]+", raw.strip()) if raw else []
    return [p for p in parts if p]


def run_daily(dry_run: bool = False) -> None:
    subreddits = _parse_subreddits(settings.subreddits)
    logger.info("Starting daily ingestion for subreddits: %s", ", ".join(subreddits))
    started_at = dt.datetime.now(tz=timezone.utc)

    reddit = RedditClient()
    total_fetched = 0
    total_relevant = 0
    total_posts_inserted = 0
    total_faqs_inserted = 0
    per_sub_counts: dict[str, dict[str, int]] = {}

    try:
        with session_scope() as session:
            for sub in subreddits:
                fetched_posts = reddit.fetch_new_posts(subreddit=sub, limit=100)
                total_fetched += len(fetched_posts)
                relevant_posts = []
                for p in fetched_posts:
                    text = f"{p.get('title','')}\n{p.get('body','')}"
                    if is_nil_relevant(text):
                        # Normalize created_utc to aware datetime
                        ts = float(p.get("created_utc") or 0.0)
                        created = dt.datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
                        relevant_posts.append(
                            {
                                "id": p.get("id"),
                                "subreddit": p.get("subreddit"),
                                "author": p.get("author"),
                                "title": p.get("title"),
                                "body": p.get("body"),
                                "score": p.get("score"),
                                "url": p.get("url"),
                                "created_utc": created,
                                "metadata": None,
                            }
                        )

                total_relevant += len(relevant_posts)

                if not dry_run and relevant_posts:
                    inserted, _ = upsert_raw_posts(session, relevant_posts)
                    total_posts_inserted += inserted

                    # Curate FAQs from relevant posts and insert
                    faq_objs = extract_faqs(relevant_posts)
                    faq_rows = [
                        {
                            "question": f.question,
                            "answer": f.answer,
                            "source_post_id": f.source_post_id,
                            "created_utc": None,
                            "updated_at": dt.datetime.now(tz=timezone.utc),
                            "tags": [],
                            "confidence": None,
                            "metadata": None,
                        }
                        for f in faq_objs
                    ]
                    ins_faqs, _ = upsert_faqs(session, faq_rows)
                    total_faqs_inserted += ins_faqs

                per_sub_counts[sub] = {
                    "fetched": len(fetched_posts),
                    "relevant": len(relevant_posts),
                }

    except Exception as e:
        finished_at = dt.datetime.now(tz=timezone.utc)
        logger.exception("Ingestion failed: %s", e)
        # Record failed run
        with session_scope() as session:
            record_ingestion_run(
                session,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                counts={
                    "total_fetched": total_fetched,
                    "total_relevant": total_relevant,
                    "total_inserted_posts": total_posts_inserted,
                    "total_inserted_faqs": total_faqs_inserted,
                    "per_subreddit": per_sub_counts,
                },
                error=str(e),
            )
        raise

    finished_at = dt.datetime.now(tz=timezone.utc)
    logger.info(
        "Ingestion completed: fetched=%d relevant=%d posts_inserted=%d faqs_inserted=%d",
        total_fetched,
        total_relevant,
        total_posts_inserted,
        total_faqs_inserted,
    )
    # Record success run
    with session_scope() as session:
        record_ingestion_run(
            session,
            started_at=started_at,
            finished_at=finished_at,
            status="success",
            counts={
                "total_fetched": total_fetched,
                "total_relevant": total_relevant,
                "total_inserted_posts": total_posts_inserted,
                "total_inserted_faqs": total_faqs_inserted,
                "per_subreddit": per_sub_counts,
            },
        )


def backfill(since: dt.date, dry_run: bool = False) -> None:
    logger.info("Backfilling since %s for subreddits: %s", since.isoformat(), settings.subreddits)
    # For MVP, reuse run_daily fetch; future: walk time windows using Reddit APIs
    run_daily(dry_run=dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="ingestion-cli", description="NIL RAG ingestion commands")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_daily = sub.add_parser("run-daily", help="Run the daily ingestion job")
    p_daily.add_argument("--dry-run", action="store_true", help="Do not call external APIs or write to DB")

    p_backfill = sub.add_parser("backfill", help="Backfill data since a given date (YYYY-MM-DD)")
    p_backfill.add_argument("--since", required=True, help="Start date inclusive, e.g. 2024-09-01")
    p_backfill.add_argument("--dry-run", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.cmd == "run-daily":
        run_daily(dry_run=bool(args.dry_run))
    elif args.cmd == "backfill":
        since = dt.date.fromisoformat(args.since)
        backfill(since=since, dry_run=bool(args.dry_run))
    else:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
