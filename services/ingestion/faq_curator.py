from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class FAQ:
    question: str
    answer: str
    source_post_id: str | None = None


def extract_faqs(posts: List[dict]) -> List[FAQ]:
    # Placeholder heuristic: pick posts that look like questions
    faqs: List[FAQ] = []
    for p in posts:
        title = (p.get("title") or "").strip()
        if title.endswith("?"):
            faqs.append(FAQ(question=title, answer="", source_post_id=p.get("id")))
    return faqs

