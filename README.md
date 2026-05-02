# EA Arch Agent

Internal AI tool for KPMG Saudi Arabia enterprise-architecture consultants.
Ingests architecture diagrams (PNG/JPEG) and produces structured analysis or
comparison output using a fully on-prem multimodal LLM (Gemma 4 via Ollama).

> **Why on-prem:** client diagrams (government entities, banks) cannot be
> uploaded to public APIs. All inference runs locally on the engagement
> workstation or a private Azure VM.

## Features (v1)

- **Analyze** — upload a single architecture diagram, pick a mode
  (Quick / Detailed / Persona-Based / User-Driven), get a streamed Markdown
  response with strengths, gaps, and recommendations.
- **Compare** — upload current + reference architectures, get a streamed
  comparison + implementation roadmap.
- **History** — past sessions persisted to Postgres; sidebar to revisit.

## Architecture

```
Browser ─▶ Nginx (prod, 443) ─▶ /EAArchAgent/         ─▶ Frontend (Vite/static)
                              ─▶ /EAArchAgent/api/*   ─▶ FastAPI (port 8000)
                                                                ├─▶ Ollama   (11434, GPU)
                                                                └─▶ Postgres (5432)
```

## Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| Backend  | FastAPI (Python 3.11) + httpx + SQLAlchemy async |
| LLM      | Ollama serving `qwen2.5vl:7b` (multimodal) |
| DB       | PostgreSQL 16                           |
| Proxy    | Nginx (production)                      |
| Runtime  | Docker Compose                          |

## Local development

Prerequisites: Docker Desktop with NVIDIA Container Toolkit, NVIDIA GPU
with ≥8 GB VRAM (qwen2.5vl:7b is ~7 GB; gemma4:26b needs ~16 GB).

**Environment**

`.env` is committed and contains the application defaults — you do **not**
need to copy it from `.env.example`. For personal overrides (e.g. a different
`OLLAMA_MODEL`, looser `CORS_ORIGINS`, or local API keys), create
`.env.local` at the repo root:

```bash
# .env.local (optional, gitignored)
OLLAMA_MODEL=gemma4:latest
CORS_ORIGINS=http://localhost:5173,http://localhost
LOG_LEVEL=DEBUG
```

`.env.local` is loaded automatically by both Pydantic Settings and
docker-compose (compose v2 `required: false`). Anything you set there
overrides `.env`.

**Bring up the stack**

```bash
# First run only — pull the LLM (~7 GB download).
docker compose up ollama ollama-pull -d
docker compose logs -f ollama-pull   # wait until "model already present"

# Full stack.
docker compose up -d
# Open http://localhost:5173/EAArchAgent/
```

**Vars the backend reads** (see `.env.example` for full descriptions):
`DATABASE_URL`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_KEEP_ALIVE`,
`BASE_PATH`, `CORS_ORIGINS`, `MAX_UPLOAD_BYTES`, `IMAGE_RESIZE_MAX_EDGE`,
`LOG_LEVEL`. The first two are auto-set by `docker-compose.yml` for local
dev; the rest come from `.env`.

## Production deployment

Deployed via the **kpmg-infra** repo, which orchestrates this app alongside
Slide-Generator and AI-Badges on a shared Azure VM. The infra repo's
deploy workflow:

1. SSHes to the VM, runs `git pull` in `/opt/apps/EA-Arch-Agent`.
2. Mounts the repo's `.env` via `env_file: /opt/apps/EA-Arch-Agent/.env`.
3. **Injects `DATABASE_URL` and `OLLAMA_HOST` as process env** — these
   point at shared services (a single Postgres and a single shared
   Ollama daemon serving all apps on the network).
4. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.

What this means for env vars:

| Var | Source in production | Source in local dev |
|---|---|---|
| `DATABASE_URL` | injected by kpmg-infra | computed from `POSTGRES_*` in `docker-compose.yml` |
| `OLLAMA_HOST` | injected by kpmg-infra | hard-coded to `http://ollama:11434` in `docker-compose.yml` |
| `OLLAMA_MODEL`, `BASE_PATH`, `CORS_ORIGINS`, `LOG_LEVEL`, etc. | committed `.env` | committed `.env` (overridable via `.env.local`) |
| Postgres credentials | managed by kpmg-infra | `POSTGRES_*` in committed `.env` (dev-only, not real secrets) |

The backend's startup validator (`validate_critical_settings()` in
`backend/app/config.py`) runs in the FastAPI lifespan and **fails fast**
if `DATABASE_URL` or `OLLAMA_HOST` are unset / placeholder strings —
surfaces orchestrator misconfiguration in the container logs the
moment it starts. Non-critical placeholders log a warning but don't
crash the container.

CI: pushing to `main` triggers `.github/workflows/deploy.yml`, a 16-line
workflow that dispatches the kpmg-infra deploy job. Operator notes for
manual hotfixes live in [CLAUDE.md](CLAUDE.md).

## Project structure

```
.
├── backend/          # FastAPI service (Phase 2)
├── frontend/         # React + Vite (Phase 3)
├── nginx/
│   └── nginx.conf    # SSE-aware reverse proxy
├── reference_images/ # Slide reference assets
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

## Deployment (Azure VM)

Deployed to a shared Azure Linux VM running docker-compose, alongside
the other kpmg apps (Slide-Generator, AI-Badges). Same convention:
- `.github/workflows/deploy.yml` dispatches the
  [amroamer/kpmg-infra](https://github.com/amroamer/kpmg-infra) deploy
  workflow on every push to `main` (requires the `INFRA_PAT` repo
  secret).
- Ollama is **shared**: one daemon on the host serves all apps via
  `host.docker.internal:11434`. Pull the model once per VM with
  `ollama pull qwen2.5vl:7b`.
- Compose joins the external `kpmg-infra_kpmg-network` so the central
  router can reach `arch-assistant-frontend` and `arch-assistant-backend`
  by alias.
- Schema + 11 seed frameworks live in [`migrations/`](migrations/);
  [`migrations/migrate.sh`](migrations/migrate.sh) runs inside the db
  container.
- Operator commands: see [CLAUDE.md](CLAUDE.md).

```bash
# On the VM:
cd /opt/EA-Arch-Agent
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Build status

Phase 1 — Scaffolding & Ollama smoke test ▶ ✅ done
Phase 2 — Backend (FastAPI + Ollama streaming + sessions DB) ▶ ✅ done
Phase 3 — Frontend scaffolding ▶ ✅ done
Phase 4 — Analyze page (Quick / Detailed / Persona / User-Driven) ▶ ✅ done
Phase 4b — Compliance mode (per-framework scorecards + editable) ▶ ✅ done
Phase 4c — Word-doc upload (.docx with embedded diagram + prose) ▶ ✅ done
Phase 5 — Compare page ▶ pending
Phase 6 — Polish & hardening ▶ pending
Phase 7 — Production deployment (alignment with kpmg-infra pattern) ▶ ✅ done

## Troubleshooting

### Ollama doesn't load `gemma4:26b`
- `docker logs arch-assistant-ollama-pull` — make sure the bootstrap pull
  completed (~9.6 GB download on first run).
- `docker exec arch-assistant-ollama ollama list` — verify the model name
  matches `OLLAMA_MODEL` in `.env`.
- The first inference call has a cold-start delay (~10–20 s) loading the
  model into VRAM. Subsequent calls are warm (`OLLAMA_KEEP_ALIVE=-1`
  pins it).

### GPU not detected inside the Ollama container
- On Windows: install the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
  and ensure Docker Desktop is in WSL 2 mode with GPU access enabled.
- Verify with `docker exec arch-assistant-ollama nvidia-smi` — should
  show your GPU and 0 running processes (until inference starts).
- If only `runc` is listed instead of `nvidia` runtime in
  `docker info | grep Runtimes`, GPU passthrough won't work.

### `/health` reports `degraded`, never reaches `ok`
- `model_loaded: false` means Ollama is up but the configured model isn't
  pulled. Run `docker compose up ollama-pull -d` and watch its logs.
- `ollama_reachable: false` means Ollama is down or unreachable on the
  network. Check `docker ps` and the `OLLAMA_HOST` env var.

### SSE responses arrive in big bursts instead of token-by-token
- Most common cause: nginx buffering. Confirm `proxy_buffering off`,
  `proxy_cache off`, `proxy_http_version 1.1`, and `gzip off` on the
  `/EAArchAgent/api/(analyze|compare)` location.
- The backend already sends `X-Accel-Buffering: no` as a fallback.
- If running behind Cloudflare, disable "Auto Minify" and add an "SSE"
  page rule that turns off proxying.

### `out of memory` errors during inference
- Check `nvidia-smi` while a request is running. `gemma4:26b` Q4_K_M
  needs ~9–10 GB VRAM with reasonable headroom for KV cache. RTX 3070 (8
  GB) won't fit; RTX 4080 / 4090 / 5090 / A6000 are comfortable.
- Symptoms: SSE stream receives `{type:"error", code:"vram_oom"}`.
- Mitigation: switch `OLLAMA_MODEL` to a smaller variant
  (`gemma4:9b`-class or `gemma3:12b`) for testing, or close other
  GPU-using apps (browsers, Stable Diffusion, etc.).

### Image upload rejected as too large
- 15 MB hard cap server-side; 4 MB target client-side after compression.
- Architecture screenshots above 4K resolution can blow past this even
  after compression. Crop to the relevant area before uploading, or
  raise `MAX_UPLOAD_BYTES` if you really need to.

### "Model in use, queued" message
- v1 serializes inference with `asyncio.Semaphore(1)` — only one analysis
  runs at a time. The second request waits its turn (the UI shows a
  queued state). For multi-user concurrency, increase the semaphore size
  and run multiple model replicas (Ollama supports `OLLAMA_NUM_PARALLEL`
  but VRAM requirements scale linearly).

## License

Internal — KPMG Saudi Arabia.
