# EA Arch Agent — Operator Notes

Quick reference for deploying and operating EA Arch Agent on the shared
Azure VM. Mirrors the structure used by `Slide-Generator` and `AI-Badges`.

## Architecture

| Tier | What | Where |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | container `arch-assistant-frontend` |
| Backend | FastAPI (Python 3.11) | container `arch-assistant-backend` |
| Database | PostgreSQL 16 | container `arch-assistant-db`, volume `postgres_data` |
| LLM | Ollama (`gemma4:26b`, ~17 GB) | **shared host daemon** at `host.docker.internal:11434` (NOT a per-app container in prod) |
| Reverse proxy | nginx | container `arch-assistant-nginx` |

The two app-facing services join the shared docker network
`kpmg-infra_kpmg-network` with stable aliases (`arch-assistant-frontend`,
`arch-assistant-backend`) so the central router can reach them.

## Deploy (the happy path)

```bash
ssh azureuser@<VM_IP>
cd /opt/EA-Arch-Agent
git pull origin main
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker restart arch-assistant-nginx        # reload routing config
```

The CI workflow `.github/workflows/deploy.yml` dispatches the
`amroamer/kpmg-infra` deploy workflow on every push to `main`; that
workflow ssh's to the VM and runs the above. Manual ssh is only for
hotfixes.

## First-time setup on a fresh VM

1. **Install Ollama on the host** (one-time per VM):
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull gemma4:26b
   systemctl enable --now ollama
   ```
   Confirm: `curl -s localhost:11434/api/tags | jq`.

2. **Clone + first deploy**:
   ```bash
   sudo mkdir -p /opt && cd /opt
   sudo git clone https://github.com/amroamer/EA-Arch-Agent.git
   cd EA-Arch-Agent
   sudo cp .env.production.example .env.production
   sudo nano .env.production            # fill in real values
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

3. **Apply migrations**:
   ```bash
   docker cp migrations/ arch-assistant-db:/tmp/migrations/
   docker exec arch-assistant-db sh -c \
     "chmod +x /tmp/migrations/*.sh && /tmp/migrations/migrate.sh"
   docker exec arch-assistant-db /tmp/migrations/verify.sh
   ```
   Should print 11 frameworks and 91 framework_items.

## Common ops

```bash
# Tail logs
docker logs --tail 100 -f arch-assistant-backend
docker logs --tail 100 -f arch-assistant-frontend

# Health check (from VM)
curl -s http://localhost/arch-assistant/api/health | jq

# Force model reload after pulling a newer Gemma
ollama pull gemma4:26b
docker restart arch-assistant-backend       # picks up the warmer model

# Database shell
docker exec -it arch-assistant-db psql -U kpmg -d kpmg_arch

# Backup the DB
docker exec arch-assistant-db pg_dump -U kpmg kpmg_arch > backup-$(date +%F).sql

# Bring everything down (keeps volumes)
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Reset everything (DESTRUCTIVE — wipes Postgres data + uploaded images)
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

## Troubleshooting

**Backend can't reach Ollama**
- `docker exec arch-assistant-backend curl -fsS http://host.docker.internal:11434/api/tags`
- If this fails, the `extra_hosts: ["host.docker.internal:host-gateway"]`
  on the backend service isn't taking effect. Check
  `docker-compose.prod.yml` and re-create the container.

**`/health` returns `degraded` with `model_loaded: false`**
- Either Ollama isn't running on the host (`systemctl status ollama`)
  or the model name in `.env.production` doesn't match what's pulled
  (`ollama list`).

**Slow first request (>30 s)**
- Cold model load into VRAM. Subsequent requests warm. Set
  `OLLAMA_KEEP_ALIVE=-1` in the host's Ollama systemd unit to pin the
  model.

**`docker compose up` fails with port 80/443 in use**
- Slide-Generator's nginx is on the same VM. The kpmg-infra repo
  decides whether `arch-assistant-nginx` binds 80/443 directly or sits
  behind a central proxy on different ports. If you hit this locally,
  comment out the `ports:` block on the `nginx` service in the prod
  override and rely on the kpmg-network alias.

**`gh` workflow dispatch returns 404**
- The `INFRA_PAT` GitHub Actions secret on
  `amroamer/EA-Arch-Agent` is missing or expired. Settings → Secrets
  and variables → Actions → New repository secret.

**`compliance` mode produces empty scorecards**
- Gemma 4's "thinking" budget is consuming all output tokens. The
  fix is already in `app/ollama_client.py:118` (`"think": False`).
  If a future model upgrade re-introduces it, revisit that flag.
