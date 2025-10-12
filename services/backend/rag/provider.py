from __future__ import annotations

from typing import Iterable, Iterator, List, Optional

from services.common.config import settings, load_yaml_secret


class LLMUnavailable(Exception):
    pass


def _openai_client():
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise LLMUnavailable("OpenAI client not installed") from e

    creds = load_yaml_secret(settings.llm_secrets_file)
    api_key = creds.get("api_key") if isinstance(creds, dict) else None
    if not api_key:
        # allow env var fallback if user set OPENAI_API_KEY manually
        import os

        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMUnavailable("OpenAI API key not configured")

    return OpenAI(api_key=api_key)


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    client = _openai_client()
    model = settings.embedding_model
    # OpenAI embeddings API accepts batch inputs
    resp = client.embeddings.create(model=model, input=list(texts))
    return [d.embedding for d in resp.data]


def stream_chat_completion(system_prompt: str, user_prompt: str) -> Iterator[str]:
    client = _openai_client()
    model = settings.llm_model
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )
    for event in stream:  # type: ignore[attr-defined]
        try:
            delta = event.choices[0].delta.content  # type: ignore[index]
        except Exception:
            delta = None
        if delta:
            yield delta

