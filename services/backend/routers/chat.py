from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from services.backend.schemas import ChatRequest
from services.backend.rag.pipeline import stream_answer


router = APIRouter()


async def _sse_from_generator(gen) -> AsyncIterator[bytes]:
    """Convert a sync text-chunk generator into an async SSE stream."""
    loop = asyncio.get_event_loop()
    done = False
    while not done:
        def _next():
            try:
                return next(gen)
            except StopIteration:
                return None

        piece = await loop.run_in_executor(None, _next)
        if piece is None:
            done = True
            break
        data = {"delta": str(piece)}
        yield ("data: " + __import__("json").dumps(data) + "\n\n").encode("utf-8")
    yield b"data: {\"done\": true}\n\n"


@router.post("/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    gen = stream_answer(req.query)
    return StreamingResponse(_sse_from_generator(gen), media_type="text/event-stream")

