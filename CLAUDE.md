# EA Arch Agent — Operator Notes

## Compliance validation layer — verification observations

**Date:** 2026-05-02 · **Mode:** `scoring_mode=single_pass` · **Doc:**
`NCGR-CSP-SAD-001_Variant-A_Strong.docx` · **Model:** `qwen2.5vl:7b`.

The validation layer (`backend/app/utils/compliance_validation.py`)
inserts three checks between Ollama's output and the SSE stream:
Pydantic schema → citation verification → evidence-rule downgrade,
plus a post-stream `validate_or_retry` that re-prompts Ollama once if
the first attempt fails ≥30% of rows or skips indices.

### Test 1 — Synthetic hallucination

**Setup:** Saved a malicious override on `analyze_compliance` instructing
the model to score every criterion 100 with `"As specified in ADR-9999."`
(ADR-9999 does not appear in the document).

**Result:** The streamed `scorecard_row` event for row 0 carried
`auto_modified: true`. The remarks field contained the server note
`[auto-downgraded: cited ADR-9999 not found in document]`. Override
deleted; defaults restored.

**Conclusion:** Citation verification correctly rejects fabricated ADR
identifiers. The downgrade-on-fabrication path works end-to-end.

### Test 2 — Real run, no-citation case (Cloud, 4 criteria)

**Setup:** Default v2 prompt, no overrides, `scoring_mode=single_pass`,
Cloud Compliance Check (4 criteria), Variant-A Strong as input.

**Result:** **All 4 rows had `auto_modified: true`**. The model emitted
non-categorical pct values (snapped via Pydantic to 100 for all four)
and **vague remarks** like *"The architecture explicitly addresses cloud
assessment and deployment model alignment with the NCGR…"* — no
ADR id, no §-number, no Table-N citation. The validator caught all
four and downgraded each to 50, appending the no-citation note. Final
weighted score: **50.0** (would have been 100 without the validator).

**Conclusion:** When the model produces narrative-only Compliant
verdicts without explicit citations, the validator forces them down to
Partial. This is the load-bearing change of this PR — vague
"looks-compliant" verdicts are no longer credible enough to ship to a
client.

### Test 3 — Schema rejection (unit-tested)

42 unit tests in `test_compliance_validation.py` cover:

- Pydantic snap-to-bucket (75 → 50, 76 → 100, 25 → 0, etc.)
- Rejection of non-numeric `compliance_pct` (e.g. `"high"`) and bool
- Empty / overlong `remarks`
- ADR / table / section regex extraction from real docs
- Placeholder-text recognition (`ADR-NNN` not flagged as a citation)
- `apply_evidence_rule`: pass-through for 50/0/null; downgrade for 100
  with no citation or fabricated-only citations; truncation when the
  appended note would push past 500 chars
- `validate_or_retry`: zero retries on a clean run, one retry when
  failure rate ≥30%, hard cap at 2 calls total, "first-attempt
  preserved if retry doesn't help" semantics

### Performance note

Single-pass + v2 prompt + 5-criterion framework + retry is **slow**
on qwen2.5vl 7B (~2 minutes worst case). The v2 prompt is verbose
(rubric + reasoning discipline + JSON-format rules) and when the model
under-emits rows (common — the v2 prompt makes it cautious), the
30%-threshold trips and adds another full Ollama round-trip. On
4-criterion frameworks (Cloud) it stays fast (~9s, no retry).

**Operational consequence:** for any framework with ≥5 criteria
running on a long doc, prefer `scoring_mode=per_criterion` — it's
both faster (parallel-feeling, ~5s per criterion) and more accurate
(focused prompt per criterion produces real ADR citations naturally).
The single-pass + v2 + validator combo is the *defensible* path, not
the *fast* path.

### What the consultant sees in the UI

A scored row with `auto_modified=true` renders with:
- Yellow tint on the row background
- `Auto-adjusted` pill above the compliance dropdown (info icon)
- The auto-note string is included in `remarks` and shown in the
  hover tooltip and the editable textarea — so the consultant
  immediately sees *why* the server flagged it.

The flag is for streaming display only; saved scorecards
(`Session.scorecards` JSON) do not persist the boolean. Schema
unchanged for downstream consumers.

---

## Compliance prompt v2 — before/after observations

**Date:** 2026-05-02 · **Document:** `NCGR-CSP-SAD-001_Variant-A_Strong.docx`
(84 833 chars; the same SAD that produced the original Q5 audit) ·
**Framework:** Infrastructure Compliance Check (5 criteria) ·
**Mode:** `scoring_mode=single_pass` (the path this PR changed) ·
**Model:** `qwen2.5vl:7b`.

### Single-pass before vs after

| Criterion | v1 (old default) | v2 (new default) |
|---|---|---|
| Q1 servers / standards (W=25) | pct=80 → Compliant *("adheres to NCGR's cloud-first … uses Kubernetes")* | pct=0 → Not Compliant *("document does not explicitly address …")* |
| Q2 tech-stack compatibility (W=20) | pct=75 → Compliant *("designed to be independent of specific vendors")* | pct=50 → Partial *("partially addresses … current technology stack")* |
| Q3 RFP integration (W=15) | pct=60 → Partial *("document does not provide a detailed RFP …")* | pct=0 → Not Compliant *("does not explicitly address the RFP clearly defining …")* |
| Q4 portability (W=15) | pct=80 → Compliant *("designed to be independent of specific vendors")* | pct=50 → Partial *("partially addresses … infrastructure and cloud design independence")* |
| Q5 network/redundancy (W=25) | pct=70 → Partial *("network design includes redundancy and failover, which is compliant")* | pct=0 → Not Compliant *("does not explicitly address the network segment …")* |
| **Weighted score** | **73.5** | **17.5** |
| Time | ~14 s | ~9 s |
| Categorical output? | No (all rows non-categorical) | Yes (every row 0 / 50 / 100) |

### Read of the trend

The headline number **dropped 56 points**, but that is the v2 prompt
working as designed:

- **v1 generously inferred Compliant** from generic-knowledge phrases
  ("uses Kubernetes", "designed to be independent of vendors") *without
  citing the document*. Several of those v1 verdicts cite no ADR ID,
  no section number, no table — exactly the kind of unfalsifiable
  "looks compliant" verdict v2 explicitly forbids.
- **v2 refuses to score 100 without a citation.** When the doc is
  silent (or truncated past 30 KB so the relevant ADR isn't visible),
  v2 falls back to 0 instead of guessing upward.
- Categorical output is now reliable: every row is one of 0/50/100.
  v1 had emitted free-form 75/80/60 which the UI silently snapped.

This is the intended trade-off — defensible scores over inflated ones.
A consultant correcting v2 upward (with the doc open) is a much
shorter review than auditing v1's hallucinations downward.

### Where the per-criterion path stands by comparison

The `scoring_mode=per_criterion` path (separate templates,
`compliance_per_criterion_v1` and `compliance_synthesis_v1`) is
unaffected by this PR — and it already scores the same Strong doc at
**100 with concrete ADR citations** (Q1=ADR-001, Q2=ADR-001, Q3=§5.3,
Q4=ADR-001, Q5=ADR-021). When you want both *defensible* and *high*
scores on a strong SAD, that's the mode to pick. The 30 KB truncation
still applies to both modes, so per-criterion's win comes from
focused-prompt attention, not extra context.

### Implications

- **Single-pass v2 is now the strict baseline.** It will under-score
  many docs versus v1, but never inflate. Use it for one-shot triage
  on suspect SADs.
- **Per-criterion remains the production-quality mode.** Slower (~5s
  per criterion vs 9s for the whole framework on v2 single-pass) but
  with real evidence and 100s where they're earned.
- **The 30 KB truncation cap is still the next bottleneck.** Lifting
  that (Phase 2 of the long-doc fix in the plan file) plus the
  per-criterion path together is the path to high-and-defensible
  scoring on long SADs.

---



Quick reference for deploying and operating EA Arch Agent on the shared
Azure VM. Mirrors the structure used by `Slide-Generator` and `AI-Badges`.

## Architecture

| Tier | What | Where |
|---|---|---|
| Frontend | React 18 + Vite + TypeScript | container `arch-assistant-frontend` |
| Backend | FastAPI (Python 3.11) | container `arch-assistant-backend` |
| Database | PostgreSQL 16 | container `arch-assistant-db`, volume `postgres_data` |
| LLM | Ollama (`qwen2.5vl:7b`, ~7 GB) | **shared host daemon** at `host.docker.internal:11434` (NOT a per-app container in prod) |
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
   ollama pull qwen2.5vl:7b
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
ollama pull qwen2.5vl:7b
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
