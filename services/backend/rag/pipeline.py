from __future__ import annotations

from typing import Iterator

from .retriever import retrieve
from .prompt import build_prompts
from .provider import stream_chat_completion, LLMUnavailable


def stream_answer(query: str) -> Iterator[str]:
    """Yield text chunks for the answer. Falls back if provider unavailable."""
    docs = retrieve(query, k=5)
    try:
        system, user = build_prompts(query, docs)
        for chunk in stream_chat_completion(system, user):
            yield chunk
    except LLMUnavailable:
        # Fallback to a simple non-LLM response
        yield (
            "Demo mode: Backend LLM not configured. "
            "When credentials are provided and the knowledge base is populated, answers will stream here."
        )

