# Migrations

SQL-based migration shape used by every app in the kpmg suite
(slide-generator, ai-badges, this one). Lives outside Alembic so a fresh
VM can be brought up reproducibly with one command.

## Files
| File | Purpose |
|---|---|
| `001_schema.sql` | Idempotent DDL — creates 4 tables (`sessions`, `images`, `frameworks`, `framework_items`) plus their PKs, FKs, indexes. Safe to re-apply. |
| `002_seed_data.sql` | TRUNCATE + INSERT of the 11 EA-Compliance frameworks (91 criteria total). Wrapped in `BEGIN; … COMMIT;`. |
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

# Seed (frameworks only — sessions/images are runtime data, not seeded)
docker exec arch-assistant-db pg_dump --data-only --no-owner \
  --no-privileges --column-inserts -U kpmg \
  -t public.frameworks -t public.framework_items kpmg_arch \
  > migrations/raw_seed.sql
# Then prepend `BEGIN; TRUNCATE … CASCADE;` and append `COMMIT;`.
```

## Why SQL and not just Alembic?

Alembic is fine for incremental deltas but requires a `stamp head` step
on a fresh DB and doesn't carry seed data. The SQL pair is what the
infra repo's deploy step calls; Alembic stays in the loop for backend
developers writing schema changes.
