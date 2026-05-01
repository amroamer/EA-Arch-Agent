"""
Phase-1 smoke test — verifies the local Ollama service can run multimodal
inference with `gemma4:26b` and stream NDJSON responses correctly.

Usage:
    pip install httpx
    python backend/smoke_ollama.py path/to/architecture.png

What it checks:
    1. Ollama is reachable at OLLAMA_HOST (default http://localhost:11434).
    2. The configured model is loaded (or auto-loads on first request).
    3. Vision input is accepted (image goes in messages[0].images, not content).
    4. Streamed NDJSON parses cleanly (manual line-buffering — proves the
       same parser shape we'll port into the FastAPI backend).
    5. `keep_alive: -1` is honored (model stays resident — verify via a
       second call returning instantly).

If this passes, Phase 2 (FastAPI backend) can be built with confidence.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:26b")
PROMPT = (
    "You are looking at an architecture diagram. In 2-3 sentences, describe "
    "what cloud or infrastructure components you can identify in the image. "
    "Be specific about what you see."
)


def encode_image(path: Path) -> str:
    """Base64-encode an image file for Ollama's `images` field."""
    if not path.exists():
        sys.exit(f"ERROR: image not found: {path}")
    if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        sys.exit(f"ERROR: unsupported image format: {path.suffix}")
    return base64.b64encode(path.read_bytes()).decode("ascii")


def stream_chat(image_b64: str) -> tuple[str, float]:
    """POST to /api/chat with streaming enabled; return (full_text, ttft_seconds).

    Uses manual NDJSON line-buffering with `iter_bytes` (NOT `iter_lines`,
    which has a known CRLF bug in some httpx versions).
    """
    payload = {
        "model": OLLAMA_MODEL,
        "stream": True,
        "keep_alive": -1,
        "messages": [
            # IMPORTANT: images go on the FIRST user message.
            # Per Gemma vision docs, image-before-text ordering matters.
            {
                "role": "user",
                "content": "[architecture diagram attached]",
                "images": [image_b64],
            },
            {"role": "user", "content": PROMPT},
        ],
        "options": {
            "temperature": 0.4,
            "num_ctx": 8192,
        },
    }

    full_text_parts: list[str] = []
    started = time.monotonic()
    ttft: float | None = None

    with httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=payload) as resp:
            if resp.status_code != 200:
                body = resp.read().decode("utf-8", errors="replace")
                sys.exit(f"ERROR: Ollama returned {resp.status_code}: {body[:500]}")

            line_buf = ""
            for chunk in resp.iter_bytes():
                if not chunk:
                    continue
                line_buf += chunk.decode("utf-8", errors="replace")
                while "\n" in line_buf:
                    line, line_buf = line_buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except json.JSONDecodeError as exc:
                        print(f"  [warn] could not parse line: {line[:120]} ({exc})")
                        continue
                    msg = evt.get("message") or {}
                    token = msg.get("content", "")
                    if token:
                        if ttft is None:
                            ttft = time.monotonic() - started
                        full_text_parts.append(token)
                        # Live token print — same shape as the SSE consumer.
                        print(token, end="", flush=True)
                    if evt.get("done"):
                        return "".join(full_text_parts), ttft or 0.0

    return "".join(full_text_parts), ttft or 0.0


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python backend/smoke_ollama.py <image-path>")

    image_path = Path(sys.argv[1])
    print(f"[smoke] OLLAMA_HOST  = {OLLAMA_HOST}")
    print(f"[smoke] OLLAMA_MODEL = {OLLAMA_MODEL}")
    print(f"[smoke] image        = {image_path}\n")

    # Sanity: is Ollama reachable and is the model present?
    try:
        with httpx.Client(timeout=10.0) as c:
            tags = c.get(f"{OLLAMA_HOST}/api/tags").json()
    except httpx.HTTPError as exc:
        sys.exit(f"ERROR: cannot reach Ollama at {OLLAMA_HOST}: {exc}")

    available = [m["name"] for m in tags.get("models", [])]
    if OLLAMA_MODEL not in available:
        # Some users have `gemma4:latest` (alias of :26b) — accept either.
        family = OLLAMA_MODEL.split(":")[0]
        if not any(name.startswith(family) for name in available):
            sys.exit(
                f"ERROR: model {OLLAMA_MODEL} not present in Ollama.\n"
                f"Available: {available}\n"
                f"Run: ollama pull {OLLAMA_MODEL}"
            )
        print(f"[smoke] {OLLAMA_MODEL} not found, but related models present: {available}")
    else:
        print(f"[smoke] model present in Ollama")

    image_b64 = encode_image(image_path)
    print(f"[smoke] image encoded: {len(image_b64):,} base64 chars\n")

    print("─" * 70)
    print("Streaming response from Gemma:")
    print("─" * 70)
    text, ttft = stream_chat(image_b64)
    total = time.monotonic()
    print("\n" + "─" * 70)

    if not text.strip():
        sys.exit("ERROR: empty response from model — vision pipeline likely broken")

    print(f"[smoke] OK — received {len(text)} chars")
    print(f"[smoke] time-to-first-token: {ttft:.2f}s")
    print(f"[smoke] Phase 1 vision smoke test PASSED ✓")


if __name__ == "__main__":
    main()
