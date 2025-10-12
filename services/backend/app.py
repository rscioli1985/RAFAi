from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI
from sqlalchemy import text

from services.common.config import settings
from services.common.db import engine
from services.common.logging import setup_logging


setup_logging()
logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"

app = FastAPI(title="NIL RAG API", version=APP_VERSION)


@app.get("/health")
def health() -> Dict[str, object]:
    db_status = "down"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "up"
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
    return {"status": "ok", "db": db_status, "version": APP_VERSION}

