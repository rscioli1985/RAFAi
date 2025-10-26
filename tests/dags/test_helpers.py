from __future__ import annotations

from datetime import datetime, timezone

from airflow_dags.dags.lib.helpers import match_keywords, to_datetime


def test_match_keywords_true_when_keyword_present() -> None:
    post = {"title": "Great Launch", "body": "We love this product"}
    assert match_keywords(post, ["launch"]) is True


def test_match_keywords_false_when_not_present() -> None:
    post = {"title": "Great Launch", "body": "We love this product"}
    assert match_keywords(post, ["angry"]) is False


def test_to_datetime_converts_timestamp() -> None:
    ts = 1_700_000_000
    result = to_datetime(ts)
    assert result == datetime.fromtimestamp(ts, tz=timezone.utc)


def test_to_datetime_handles_invalid() -> None:
    assert to_datetime("not-a-number") is None
