from __future__ import annotations

from typing import Iterable, List

from services.common.config import settings


def compute_embeddings(texts: Iterable[str]) -> List[list[float]]:
    """Stub for embedding generation.

    Implementation can call provider SDKs (e.g., OpenAI) using `settings.embedding_model`.
    Left unimplemented in the MVP skeleton to avoid network calls by default.
    """
    # TODO: implement using provider client (e.g., openai.Embeddings.create)
    raise NotImplementedError("Embedding generation not implemented in skeleton")

