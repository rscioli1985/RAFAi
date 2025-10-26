from __future__ import annotations

import importlib
from pathlib import Path

import pytest

try:
    import airflow  # type: ignore
except ImportError:  # pragma: no cover
    airflow = None


@pytest.mark.skipif(airflow is None, reason="Airflow not installed; skipping DAG import tests.")
def test_dag_modules_import() -> None:
    dags_dir = Path(__file__).resolve().parents[1] / "airflow_dags" / "dags"
    dag_files = sorted(p.stem for p in dags_dir.glob("*.py") if p.name != "__init__.py")
    assert dag_files, "No DAG files found to import."
    for module_name in dag_files:
        importlib.import_module(f"airflow_dags.dags.{module_name}")
