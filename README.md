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
Browser ─▶ Nginx (prod, 443) ─▶ /arch-assistant/         ─▶ Frontend (Vite/static)
                              ─▶ /arch-assistant/api/*   ─▶ FastAPI (port 8000)
                                                                ├─▶ Ollama   (11434, GPU)
                                                                └─▶ Postgres (5432)
```

## Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Frontend | React 18 + Vite + TypeScript + Tailwind + shadcn/ui |
| Backend  | FastAPI (Python 3.11) + httpx + SQLAlchemy async |
| LLM      | Ollama serving `gemma4:26b` (multimodal)|
| DB       | PostgreSQL 16                           |
| Proxy    | Nginx (production)                      |
| Runtime  | Docker Compose                          |

## Quick start (local dev)

Prerequisites: Docker Desktop with NVIDIA Container Toolkit, NVIDIA GPU
with ≥16 GB VRAM (RTX 4090 / 5090 / A6000 / etc.).

```bash
# 1. Configure environment
cp .env.example .env

# 2. Bring up Ollama and pull the model (first run only — ~9.6 GB download)
docker compose up ollama ollama-pull -d
docker compose logs -f ollama-pull   # wait until "model already present"

# 3. Phase-1 smoke test — verify multimodal inference works
pip install httpx
python backend/smoke_ollama.py path/to/any-architecture.png

# (Phase 2+) bring up the full stack
docker compose up -d
# Open http://localhost:5173/arch-assistant/
```

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

## Build status

Phase 1 — Scaffolding & Ollama smoke test ▶ **in progress**
Phase 2 — Backend (FastAPI + Ollama streaming + sessions DB) ▶ pending
Phase 3 — Frontend scaffolding ▶ pending
Phase 4 — Analyze page (4 modes) ▶ pending
Phase 5 — Compare page ▶ pending
Phase 6 — Polish & hardening ▶ pending
Phase 7 — Production deployment ▶ pending

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
  `/arch-assistant/api/(analyze|compare)` location.
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
