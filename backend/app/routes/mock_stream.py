"""GET /mock-stream — canned SSE stream for frontend SSE-consumer testing.

Useful in Phase 3 before the real model is loaded: hits the same SSE
plumbing (StreamingResponse + nginx-buffering headers) as /analyze and
/compare without paying Gemma latency. Remove or gate behind DEBUG when
the app reaches production.
"""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

CANNED_RESPONSE = """## Architecture Overview
This is a synthetic streamed response for SSE-plumbing testing.

## Key Strengths
- Multi-AZ deployment.
- Encrypted at rest and in transit.
- Auto-scaling group sized for peak load.

## Top Concerns
- Single NAT gateway in Region A.
- IAM role has overly broad S3 access.

## Recommended Next Steps
- Add a second NAT gateway for HA.
- Tighten IAM permissions to specific buckets.
- Enable VPC flow logs.
"""


def _sse(payload: dict) -> bytes:
    return f"data: {json.dumps(payload, separators=(',', ':'))}\n\n".encode()


@router.get("/mock-stream")
async def mock_stream() -> StreamingResponse:
    async def gen() -> AsyncIterator[bytes]:
        yield _sse({"type": "session_created", "id": "mock-0000"})
        # Stream word-by-word with a short delay so the consumer sees real
        # incremental output.
        for token in CANNED_RESPONSE.split(" "):
            yield _sse({"type": "token", "content": token + " "})
            await asyncio.sleep(0.04)
        yield _sse({"type": "done", "ttft_ms": 40, "total_ms": 1500})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
