# Migrations

SQL-based migration shape used by every app in the kpmg suite
(slide-generator, ai-badges, this one). Lives outside Alembic so a fresh
VM can be brought up reproducibly with one command.

## Files
| File | Purpose |
|---|---|
| `001_schema.sql` | Idempotent DDL — creates 6 tables (`sessions`, `images`, `frameworks`, `framework_items`, `prompt_overrides`, `llm_config`) plus their PKs, FKs, indexes. Safe to re-apply. |
| `002_seed_data.sql` | Seeds the 10 EA-Compliance frameworks (93 criteria) **destructively** — TRUNCATE + INSERT, so re-runs match local exactly. The `prompt_overrides` and `llm_config` sections are **non-destructive** — INSERT … ON CONFLICT DO NOTHING — so user customisations on the server are preserved. Wrapped in `BEGIN; … COMMIT;`. |
| `migrate.sh` | Orchestrates schema → verify → seed → row counts. Runs **inside the db container** (uses `psql`, not Docker). |
| `verify.sh` | Read-only sanity check: tables present, row counts ≥ baseline, scorecards column present. |

## Usage on the VM

```bash
# Copy the folder INTO the running db container.
docker cp migrations/ arch-assistant-db:/tmp/migrations/

# Apply — schema is idempotent, seed truncates-then-inserts.
docker exec arch-assistant-db sh -c \
  "chmod +x /tmp/migrations/*.sh && /tmp/migrations/migrate.sh"

# Verify (read-only).
docker exec arch-assistant-db /tmp/migrations/verify.sh
```

## Local dev

```bash
# Against the running dev DB (port 5432, default creds from .env):
PSQL="postgresql://kpmg:kpmg@localhost:5432/kpmg_arch"
psql "$PSQL" -f migrations/001_schema.sql
psql "$PSQL" -f migrations/002_seed_data.sql
```

## Regenerating

After schema changes (add a column, new table, etc.):

```bash
# Schema
docker exec arch-assistant-db pg_dump --schema-only --no-owner \
  --no-privileges --no-comments -U kpmg kpmg_arch \
  > migrations/001_schema.sql
# Then run scripts/fix_schema_idempotent.py (or hand-edit) to wrap CREATEs
# with IF NOT EXISTS and ADD CONSTRAINTs in DO blocks.

# Seed (frameworks + prompts + llm_config — sessions/images are runtime
# data, not seeded). Includes any prompt overrides and LLM config the
# local user has saved via the Settings UI; the seed script will then
# attempt to insert them on the target without overwriting existing
# server-side values.
docker exec arch-assistant-db pg_dump --data-only --no-owner \
  --no-privileges --column-inserts -U kpmg \
  -t public.frameworks -t public.framework_items \
  -t public.prompt_overrides -t public.llm_config \
  kpmg_arch > migrations/raw_seed.sql
# Splice the resulting INSERT blocks into the four sections of
# 002_seed_data.sql (frameworks, framework_items, prompt_overrides,
# llm_config). The frameworks/items sections sit between TRUNCATE and
# COMMIT; the prompt_overrides + llm_config rows need an explicit
# `ON CONFLICT (key|id) DO NOTHING` clause appended to each INSERT (see
# the comment-stub examples already in the file).
```

## Why SQL and not just Alembic?

Alembic is fine for incremental deltas but requires a `stamp head` step
on a fresh DB and doesn't carry seed data. The SQL pair is what the
infra repo's deploy step calls; Alembic stays in the loop for backend
developers writing schema changes.
