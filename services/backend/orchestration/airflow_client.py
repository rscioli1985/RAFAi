from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx

from services.common.config import settings


logger = logging.getLogger(__name__)


class AirflowClientError(RuntimeError):
    """Represents failures while communicating with Airflow's REST API."""


@dataclass(slots=True)
class AirflowClient:
    base_url: str
    username: Optional[str]
    password: Optional[str]
    api_token: Optional[str]
    verify_ssl: bool
    timeout: float
    mock_mode: bool

    @classmethod
    def from_settings(cls) -> "AirflowClient":
        return cls(
            base_url=settings.airflow_base_url,
            username=settings.airflow_username,
            password=settings.airflow_password,
            api_token=settings.airflow_api_token,
            verify_ssl=settings.airflow_verify_ssl,
            timeout=settings.airflow_timeout_seconds,
            mock_mode=settings.airflow_use_mock,
        )

    def trigger_dag_run(self, dag_id: str, conf: Dict[str, Any]) -> str:
        """Trigger a DAG run and return the Airflow dag_run_id."""

        if self.mock_mode:
            run_id = f"mock-{uuid.uuid4()}"
            logger.info("[AirflowMock] Trigger DAG %s -> %s", dag_id, run_id)
            return run_id

        url = self._dag_run_url(dag_id)
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        auth: Optional[Tuple[str, str]] = None
        if self.username and self.password:
            auth = (self.username, self.password)

        payload = {"conf": conf}
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=headers,
                auth=auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except httpx.HTTPError as exc:
            raise AirflowClientError(f"Failed to trigger DAG {dag_id}: {exc}") from exc

        if response.status_code >= 300:
            raise AirflowClientError(
                f"Airflow responded with {response.status_code}: {response.text}"
            )

        data = response.json()
        run_id = data.get("dag_run_id") or data.get("id")
        if not run_id:
            raise AirflowClientError("Airflow response missing dag_run_id")
        return run_id

    def get_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        """Fetch metadata about a specific dag run."""

        if self.mock_mode:
            return {
                "dag_id": dag_id,
                "dag_run_id": dag_run_id,
                "state": "success",
                "start_date": None,
                "end_date": None,
            }

        url = f"{self._dag_run_url(dag_id)}/{dag_run_id}"
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        auth: Optional[Tuple[str, str]] = None
        if self.username and self.password:
            auth = (self.username, self.password)

        try:
            response = httpx.get(
                url,
                headers=headers,
                auth=auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except httpx.HTTPError as exc:
            raise AirflowClientError(f"Failed to fetch dag run {dag_run_id}: {exc}") from exc

        if response.status_code == 404:
            raise AirflowClientError(f"DAG run {dag_run_id} not found for DAG {dag_id}")

        if response.status_code >= 300:
            raise AirflowClientError(
                f"Airflow responded with {response.status_code} for dag run {dag_run_id}: {response.text}"
            )

        return response.json()

    def _dag_run_url(self, dag_id: str) -> str:
        base = self.base_url.rstrip("/")
        if not base.endswith("/api/v1"):
            base = f"{base}/api/v1"
        return f"{base}/dags/{dag_id}/dagRuns"
