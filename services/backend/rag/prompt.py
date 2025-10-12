from __future__ import annotations

from typing import List

from .retriever import RetrievedDoc


def build_prompts(query: str, docs: List[RetrievedDoc]) -> tuple[str, str]:
    system = (
        "You are a helpful assistant that answers questions about NIL (Name, Image, and Likeness). "
        "Use the provided context excerpts to craft a precise, concise answer. Cite sources by including the Reddit URL when relevant. "
        "If the answer is uncertain or not present, state that clearly."
    )

    if docs:
        context_parts = []
        for i, d in enumerate(docs, start=1):
            url = None
            if d.metadata and isinstance(d.metadata, dict):
                url = d.metadata.get("url")
            context_parts.append(f"[{i}] {d.text[:1200]}" + (f"\nSource: {url}" if url else ""))
        context = "\n\n".join(context_parts)
        user = (
            "Question: "
            + query
            + "\n\nContext:\n"
            + context
            + "\n\nInstructions: Answer using only the context when possible. Include source numbers like [1], [2] if relevant."
        )
    else:
        user = (
            "Question: "
            + query
            + "\n\nContext: (no context available)\nInstructions: Answer briefly and note that citations are unavailable."
        )

    return system, user

