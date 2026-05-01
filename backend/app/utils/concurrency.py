"""Process-wide concurrency primitives.

A single Ollama-serving model can only run one inference at a time on its
GPU. Multiple FastAPI workers fighting over it produces unpredictable
latency and queueing behavior. We serialize at the application layer with
a semaphore.
"""
from __future__ import annotations

import asyncio

# Process-wide. Increase to N if you start running N model replicas.
ollama_semaphore: asyncio.Semaphore = asyncio.Semaphore(1)
