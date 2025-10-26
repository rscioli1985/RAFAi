from __future__ import annotations

import logging
from typing import Dict

from fastapi import FastAPI, Response
from sqlalchemy import text

from services.backend.graphql import graphql_router
from services.backend.routes import auth_router, subreddits_router, keywords_router
from services.common.config import settings
from services.common.db import engine
from services.common.logging import setup_logging
from services.common.metrics import render_prometheus_metrics


setup_logging()
logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"

app = FastAPI(title="NIL RAG API", version=APP_VERSION)
app.include_router(graphql_router, prefix="/graphql")
app.include_router(auth_router)
app.include_router(subreddits_router)
app.include_router(keywords_router)


@app.get("/api/health")
def health() -> Dict[str, object]:
    db_status = "down"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "up"
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
    return {"status": "ok", "db": db_status, "version": APP_VERSION}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    payload, content_type = render_prometheus_metrics()
    return Response(content=payload, media_type=content_type)
