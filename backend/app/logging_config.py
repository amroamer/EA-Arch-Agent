"""Structured JSON logging configuration.

Switches the root logger to a single JSON-formatted handler so logs are
easily parseable in Loki/CloudWatch/Splunk. Each request to the analyze /
compare endpoints emits a structured log line with mode, image bytes,
TTFT, and total duration (handlers attach those fields via `extra=`).
"""
from __future__ import annotations

import logging
import sys

from pythonjsonlogger import jsonlogger

from app.config import settings


def configure_logging() -> None:
    """Replace any existing root handlers with a single JSON-formatted one."""
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "ts", "levelname": "level"},
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Calm uvicorn's access logger — it's fine but noisy on /health polls.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
