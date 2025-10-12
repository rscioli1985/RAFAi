from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

import sqlalchemy as sa
from sqlalchemy import text

from services.common.db import engine
from .provider import embed_texts, LLMUnavailable


@dataclass
class RetrievedDoc:
    id: int
    text: str
    metadata: Dict[str, Any] | None
    distance: float


def _to_vector_literal(vec: list[float]) -> str:
    # pgvector literal: '[v1, v2, ...]'
    # limit precision for readability; DB stores full precision internally
    return "[" + ", ".join(f"{x:.6f}" for x in vec) + "]"


def retrieve(query: str, k: int = 5) -> List[RetrievedDoc]:
    try:
        q_embed = embed_texts([query])[0]
    except LLMUnavailable:
        return []

    vec = _to_vector_literal(q_embed)
    sql = f"""
        SELECT d.id, d.text, d.metadata, (e.embedding <-> '{vec}') AS distance
        FROM embeddings e
        JOIN documents d ON d.id = e.document_id
        ORDER BY distance ASC
        LIMIT :k
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"k": k}).mappings().all()
    results: List[RetrievedDoc] = []
    for r in rows:
        results.append(
            RetrievedDoc(
                id=int(r["id"]),
                text=str(r["text"] or ""),
                metadata=r.get("metadata"),
                distance=float(r["distance"] if r["distance"] is not None else 0.0),
            )
        )
    return results

