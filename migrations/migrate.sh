#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────
# EA Arch Agent — schema + seed migration  (POSIX sh; runs on alpine)
#
# Runs INSIDE the db container (pure psql, no docker commands).
#
# Usage (on the VM):
#   docker cp migrations/ arch-assistant-db:/tmp/migrations/
#   docker exec arch-assistant-db sh /tmp/migrations/migrate.sh
#
# Or with an explicit DATABASE_URL:
#   ./migrate.sh "postgresql://kpmg:kpmg@localhost:5432/kpmg_arch"
#
# Steps:
#   1. Apply 001_schema.sql (idempotent: CREATE TABLE IF NOT EXISTS …)
#   2. Verify the expected tables exist
#   3. Apply 003_add_rationale_columns.sql (additive ALTER TABLE; safe on
#      fresh and populated DBs; must run BEFORE the seed because 002's
#      INSERTs reference the new columns)
#   4. Apply 002_seed_data.sql (TRUNCATEs framework_items + frameworks,
#      then INSERTs the seed with rationale baked in)
#   5. Apply 004_backfill_rationale.sql (no-op when 002 has just run;
#      safety net for partial-migration scenarios)
#   6. Print row counts for verification
# ─────────────────────────────────────────────────────────────────────────
set -eu

GREEN=''; RED=''; YELLOW=''; NC=''
if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
fi

log()  { printf '%b[MIGRATE]%b %s\n' "$GREEN" "$NC" "$*"; }
warn() { printf '%b[WARN]%b %s\n'    "$YELLOW" "$NC" "$*"; }
err()  { printf '%b[ERROR]%b %s\n'   "$RED" "$NC" "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCHEMA_FILE="$SCRIPT_DIR/001_schema.sql"
SEED_FILE="$SCRIPT_DIR/002_seed_data.sql"
RATIONALE_SCHEMA_FILE="$SCRIPT_DIR/003_add_rationale_columns.sql"
RATIONALE_BACKFILL_FILE="$SCRIPT_DIR/004_backfill_rationale.sql"

if [ -n "${1:-}" ]; then
    DATABASE_URL="$1"
    export DATABASE_URL
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-kpmg}"
DB_NAME="${DB_NAME:-kpmg_arch}"

if [ -n "${DATABASE_URL:-}" ]; then
    PSQL_CONN="$DATABASE_URL"
else
    PSQL_CONN="postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
fi

[ -f "$SCHEMA_FILE" ]             || err "001_schema.sql not found in $SCRIPT_DIR"
[ -f "$SEED_FILE" ]               || err "002_seed_data.sql not found in $SCRIPT_DIR"
[ -f "$RATIONALE_SCHEMA_FILE" ]   || err "003_add_rationale_columns.sql not found in $SCRIPT_DIR"
[ -f "$RATIONALE_BACKFILL_FILE" ] || err "004_backfill_rationale.sql not found in $SCRIPT_DIR"

# Test connection
psql "$PSQL_CONN" -c "SELECT 1;" >/dev/null 2>&1 \
    || err "Cannot connect to database. Check DATABASE_URL or DB_USER/DB_NAME."

run_sql() { psql "$PSQL_CONN" "$@"; }

# ── Step 1: Schema ──
log "Step 1/6: Applying schema (6 tables) …"
run_sql -v ON_ERROR_STOP=1 -f "$SCHEMA_FILE" >/dev/null
log "Schema applied."

# ── Step 2: Verify tables ──
log "Step 2/6: Verifying schema …"
MISSING=0
for tbl in sessions images frameworks framework_items prompt_overrides llm_config; do
    n=$(psql -t -A "$PSQL_CONN" -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='$tbl';" 2>/dev/null)
    if [ "$n" != "1" ]; then
        warn "Missing table: $tbl"
        MISSING=$((MISSING + 1))
    fi
done
[ "$MISSING" -eq 0 ] || err "$MISSING table(s) missing. Check schema migration output."
log "All 6 tables verified."

# ── Step 3: Additive schema migrations (must run BEFORE seed) ──
log "Step 3/6: Applying additive schema migrations (003 …) …"
log "  → 003_add_rationale_columns.sql"
run_sql -v ON_ERROR_STOP=1 -f "$RATIONALE_SCHEMA_FILE" >/dev/null
log "Additive schema migrations applied."

# ── Step 4: Seed ──
log "Step 4/6: Applying seed data (frameworks + items, plus prompts/llm_config if present) …"
run_sql -v ON_ERROR_STOP=1 -f "$SEED_FILE" >/dev/null
log "Seed applied."

# ── Step 5: Data backfill safety net (no-op when 002 has just run) ──
log "Step 5/6: Applying data backfills (004 …) …"
log "  → 004_backfill_rationale.sql"
run_sql -v ON_ERROR_STOP=1 -f "$RATIONALE_BACKFILL_FILE" >/dev/null
log "Data backfills applied."

# ── Step 6: Row counts ──
log "Step 6/6: Verifying row counts …"
echo
echo "=== Row Counts ==="
run_sql -c "
    SELECT 'frameworks'        AS table_name, COUNT(*) AS rows FROM frameworks
    UNION ALL SELECT 'framework_items',  COUNT(*) FROM framework_items
    UNION ALL SELECT 'prompt_overrides', COUNT(*) FROM prompt_overrides
    UNION ALL SELECT 'llm_config',       COUNT(*) FROM llm_config
    UNION ALL SELECT 'sessions',         COUNT(*) FROM sessions
    UNION ALL SELECT 'images',           COUNT(*) FROM images
    ORDER BY table_name;
"
echo
log "Migration finished successfully."
