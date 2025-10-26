from __future__ import annotations

import logging
import os
import random
from hashlib import sha256
from typing import Iterable, List

from openai import OpenAI, OpenAIError

from services.common import metrics
from services.common.config import settings

logger = logging.getLogger(__name__)
_openai_client: OpenAI | None = None


def compute_embeddings(texts: Iterable[str]) -> List[List[float]]:
    input_texts = list(texts)
    if not input_texts:
        return []

    client = _get_openai_client()
    if client is not None:
        try:
            response = client.embeddings.create(
                model=settings.embedding_model,
                input=input_texts,
            )
            vectors = [record.embedding for record in response.data]
            # Embeddings responses include usage tokens per batch in some models; fall back to heuristic.
            tokens = getattr(getattr(response, "usage", None), "total_tokens", None)
            if tokens is None:
                tokens = _estimate_tokens(input_texts)
            metrics.record_llm_tokens(settings.embedding_model, tokens)
            return vectors
        except OpenAIError as exc:  # pragma: no cover - network dependent
            logger.warning("OpenAI embedding request failed, falling back to deterministic vectors: %s", exc)
        except Exception as exc:  # pragma: no cover
            logger.warning("Unexpected embedding error, falling back to deterministic vectors: %s", exc)

    fallback_vectors = [_deterministic_embedding(text, settings.vector_dim) for text in input_texts]
    metrics.record_llm_tokens(settings.embedding_model, _estimate_tokens(input_texts))
    return fallback_vectors


def _get_openai_client() -> OpenAI | None:
    global _openai_client
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    if _openai_client is None:
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _deterministic_embedding(text: str, dims: int) -> List[float]:
    seed = int(sha256(text.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    vector = [rng.uniform(-1, 1) for _ in range(dims)]
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]


def _estimate_tokens(texts: Iterable[str]) -> int:
    total = 0
    for text in texts:
        total += max(1, len((text or "").split()))
    return total
