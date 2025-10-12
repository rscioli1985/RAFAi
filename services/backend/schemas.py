from __future__ import annotations

from pydantic import BaseModel
from typing import Any, Dict, Optional


class ChatRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None


class ChatChunk(BaseModel):
    delta: str
    done: bool = False
    # Optional: add citations/metadata later

