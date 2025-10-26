from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv
import yaml


# Load .env from project root, if present
load_dotenv()


def _getenv_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    api_key: Optional[str] = os.getenv("API_KEY")

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://app:app@localhost:5432/nilrag"
    )

    vector_dim: int = int(os.getenv("VECTOR_DIM", "1536"))

    secrets_dir: Optional[str] = os.getenv("SECRETS_DIR")
    reddit_secrets_file: Optional[str] = os.getenv("REDDIT_SECRETS_FILE")
    llm_secrets_file: Optional[str] = os.getenv("LLM_SECRETS_FILE")

    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    subreddits: str = os.getenv("SUBREDDITS", "exampleSub1+exampleSub2")
    backfill_days: int = int(os.getenv("BACKFILL_DAYS", "30"))
    max_subreddits_per_job: int = int(os.getenv("MAX_SUBREDDITS_PER_JOB", "10"))
    max_keywords_per_job: int = int(os.getenv("MAX_KEYWORDS_PER_JOB", "50"))
    llm_daily_budget_cents: int = int(os.getenv("LLM_DAILY_BUDGET_CENTS", "5000"))
    feature_run_scrape: bool = _getenv_bool("FEATURE_RUN_SCRAPE", True)
    feature_reanalyze: bool = _getenv_bool("FEATURE_REANALYZE", True)
    feature_reembed: bool = _getenv_bool("FEATURE_REEMBED", True)

    airflow_base_url: str = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
    airflow_username: Optional[str] = os.getenv("AIRFLOW_USERNAME")
    airflow_password: Optional[str] = os.getenv("AIRFLOW_PASSWORD")
    airflow_api_token: Optional[str] = os.getenv("AIRFLOW_API_TOKEN")
    airflow_verify_ssl: bool = _getenv_bool("AIRFLOW_VERIFY_SSL", False)
    airflow_use_mock: bool = _getenv_bool("AIRFLOW_USE_MOCK", True)
    airflow_timeout_seconds: float = float(os.getenv("AIRFLOW_TIMEOUT_SECONDS", "10"))


settings = Settings()


def load_yaml_secret(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
