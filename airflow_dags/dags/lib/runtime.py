from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ENV_PATH = PROJECT_ROOT / ".env"

# Ensure local .env is loaded even when Airflow runs from a different CWD.
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)
else:
    load_dotenv(override=False)

ROOT_STR = str(PROJECT_ROOT)
if ROOT_STR not in sys.path:
    sys.path.append(ROOT_STR)


def init_logging() -> None:
    """Configure a consistent log format/level for DAG tasks."""

    level_name = os.getenv("AIRFLOW_TASK_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


__all__ = ["PROJECT_ROOT", "init_logging"]
