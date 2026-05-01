"""Smoke test for the /health endpoint.

Verifies that the route is wired up under the configured base_path. Does
not require Ollama to be reachable — health degrades gracefully when it
isn't.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_payload(client: TestClient) -> None:
    response = client.get(f"{settings.base_path}/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert body["status"] in {"ok", "degraded", "down"}
    assert "ollama_reachable" in body
    assert "model_loaded" in body
    assert "uptime_seconds" in body
    assert body["model_name"] == settings.ollama_model
