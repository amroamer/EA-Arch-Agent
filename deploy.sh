#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────
# EA Arch Agent — production deploy script.
#
# Pulls latest from git, rebuilds the prod stack, and runs a health check.
# Intended to run on the Azure VM (NC-series for GPU, or fall back to a
# CPU-only smaller model on non-GPU hosts).
# ─────────────────────────────────────────────────────────────────────────
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/arch-assistant}"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
HEALTH_URL="${HEALTH_URL:-https://arch-assistant.kpmg.example/arch-assistant/api/health}"

cd "$PROJECT_DIR"

echo "[deploy] pulling latest from git…"
git pull --ff-only

echo "[deploy] verifying .env.production exists…"
if [[ ! -f .env.production ]]; then
  echo "ERROR: .env.production is missing. Copy .env.example and fill in." >&2
  exit 1
fi

echo "[deploy] pulling latest images from the registry…"
# shellcheck disable=SC2086
docker compose ${COMPOSE_FILES} pull
# Fallback: in-place build if the registry doesn't have an image for the
# current commit (e.g., during a hotfix). Comment out the pull above and
# uncomment the next line to rebuild on the VM.
# docker compose ${COMPOSE_FILES} up -d --build

echo "[deploy] (re)starting services…"
# shellcheck disable=SC2086
docker compose ${COMPOSE_FILES} up -d

echo "[deploy] waiting for backend to become ready…"
for i in {1..30}; do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "[deploy] backend healthy after ${i}0s"
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "ERROR: backend did not become healthy in 5 minutes" >&2
    docker compose ${COMPOSE_FILES} logs --tail 60 backend
    exit 2
  fi
  sleep 10
done

echo "[deploy] final health check:"
curl -fsS "$HEALTH_URL" | python3 -m json.tool || true

echo "[deploy] done."
