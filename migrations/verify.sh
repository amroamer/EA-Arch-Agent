#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────
# EA Arch Agent — DB sanity check  (POSIX sh; runs on alpine busybox)
#
# Read-only — confirms the schema is applied and the seed frameworks
# are present. Safe to run anytime.
#
# Usage (on the VM):
#   docker exec arch-assistant-db /tmp/migrations/verify.sh
# Or with explicit DSN:
#   ./verify.sh "postgresql://kpmg@localhost:5432/kpmg_arch"
# ─────────────────────────────────────────────────────────────────────────
set -eu

GREEN=''; RED=''; YELLOW=''; NC=''
if [ -t 1 ]; then
    GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
fi

ok()   { printf '%b[OK]%b    %s\n'   "$GREEN" "$NC" "$*"; }
warn() { printf '%b[WARN]%b  %s\n'   "$YELLOW" "$NC" "$*"; }
err()  { printf '%b[FAIL]%b  %s\n'   "$RED" "$NC" "$*"; FAILED=1; }

FAILED=0

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

run_sql() {
    psql -t -A "$PSQL_CONN" -c "$1" 2>/dev/null
}

# ── Connection ──
if psql "$PSQL_CONN" -c "SELECT 1;" >/dev/null 2>&1; then
    ok "Database reachable"
else
    err "Cannot connect to $PSQL_CONN"
    exit 2
fi

# ── Tables ──
for tbl in sessions images frameworks framework_items prompt_overrides llm_config; do
    n=$(run_sql "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='$tbl';")
    if [ "$n" = "1" ]; then
        ok "Table present: $tbl"
    else
        err "Table missing: $tbl"
    fi
done

# ── Row counts ──
fwc=$(run_sql "SELECT COUNT(*) FROM frameworks;")
fic=$(run_sql "SELECT COUNT(*) FROM framework_items;")
poc=$(run_sql "SELECT COUNT(*) FROM prompt_overrides;")
lcc=$(run_sql "SELECT COUNT(*) FROM llm_config;")
if [ "$fwc" -ge 10 ]; then ok   "frameworks rows: $fwc (expected >= 10)"
else                            warn "frameworks rows: $fwc (expected >= 10)"
fi
if [ "$fic" -ge 90 ]; then ok   "framework_items rows: $fic (expected >= 90)"
else                            warn "framework_items rows: $fic (expected >= 90)"
fi
ok "prompt_overrides rows: $poc (any count is fine — user-managed)"
ok "llm_config rows: $lcc (0 = using defaults; 1 = user override active)"

# ── Compliance-mode column ──
sc=$(run_sql "SELECT COUNT(*) FROM information_schema.columns WHERE table_name='sessions' AND column_name='scorecards';")
if [ "$sc" = "1" ]; then
    ok "sessions.scorecards column present (compliance mode)"
else
    err "sessions.scorecards column missing — run migrate.sh"
fi

if [ "$FAILED" -eq 0 ]; then
    echo
    printf '%bAll checks passed.%b\n' "$GREEN" "$NC"
else
    echo
    printf '%bOne or more checks failed.%b\n' "$RED" "$NC"
    exit 1
fi
