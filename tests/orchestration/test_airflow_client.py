from __future__ import annotations

from typing import Any

import httpx
import pytest

from services.backend.orchestration.airflow_client import AirflowClient, AirflowClientError


def test_trigger_dag_run_mock_mode() -> None:
    client = AirflowClient(
        base_url="http://localhost",
        username=None,
        password=None,
        api_token=None,
        verify_ssl=False,
        timeout=1,
        mock_mode=True,
    )
    run_id = client.trigger_dag_run("example", {"foo": "bar"})
    assert run_id.startswith("mock-")


def test_get_dag_run_success(monkeypatch) -> None:
    payload = {"dag_run_id": "manual__2024", "state": "success"}

    def fake_get(url: str, **_: Any) -> httpx.Response:
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(httpx, "get", fake_get)
    client = AirflowClient(
        base_url="http://localhost",
        username=None,
        password=None,
        api_token=None,
        verify_ssl=False,
        timeout=1,
        mock_mode=False,
    )
    result = client.get_dag_run("example", "manual__2024")
    assert result == payload


def test_get_dag_run_raises_on_error(monkeypatch) -> None:
    def fake_get(url: str, **_: Any) -> httpx.Response:
        return httpx.Response(500, text="boom")

    monkeypatch.setattr(httpx, "get", fake_get)
    client = AirflowClient(
        base_url="http://localhost",
        username=None,
        password=None,
        api_token=None,
        verify_ssl=False,
        timeout=1,
        mock_mode=False,
    )
    with pytest.raises(AirflowClientError):
        client.get_dag_run("example", "manual__2024")
