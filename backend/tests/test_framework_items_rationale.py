"""Tests that the rationale columns are properly seeded.

These tests run against the seed SQL files directly (no live DB required)
because the existing test infrastructure is unit-only — there is no
fixture for spinning up Postgres. We assert structural properties of the
SQL itself: every framework_items INSERT carries non-NULL rationale and
every value fits the ≤200-char content rule.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = REPO_ROOT / "migrations"
SCHEMA_FILE = MIGRATIONS / "001_schema.sql"
SEED_FILE = MIGRATIONS / "002_seed_data.sql"
RATIONALE_SCHEMA_FILE = MIGRATIONS / "003_add_rationale_columns.sql"
BACKFILL_FILE = MIGRATIONS / "004_backfill_rationale.sql"

EXPECTED_ITEM_COUNT = 93
MAX_RATIONALE_CHARS = 200


# Match: INSERT INTO public.framework_items (col1,col2,...) VALUES (val1,val2,...);
# Captures the (col list) and the (val list) groups separately so we can
# pair fields with values without depending on PostgreSQL.
_INSERT_RE = re.compile(
    r"INSERT INTO public\.framework_items\s*\(([^)]+)\)\s*VALUES\s*\((.*?)\)\s*;",
    re.DOTALL,
)


def _split_sql_values(blob: str) -> list[str]:
    """Split a SQL VALUES list into individual literals.

    Walks the string respecting single-quote string boundaries and the
    SQL doubled-quote escape (`''` inside a string is a literal `'`).
    Splits on top-level commas only.
    """
    out: list[str] = []
    cur: list[str] = []
    in_str = False
    i = 0
    while i < len(blob):
        ch = blob[i]
        if in_str:
            if ch == "'" and i + 1 < len(blob) and blob[i + 1] == "'":
                # Escaped quote — consume both.
                cur.append("''")
                i += 2
                continue
            cur.append(ch)
            if ch == "'":
                in_str = False
            i += 1
            continue
        if ch == "'":
            in_str = True
            cur.append(ch)
            i += 1
            continue
        if ch == ",":
            out.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if cur:
        out.append("".join(cur).strip())
    return out


def _unquote(literal: str) -> str | None:
    """Convert a SQL string literal or NULL to a Python str (or None)."""
    s = literal.strip()
    if s.upper() == "NULL":
        return None
    if not (s.startswith("'") and s.endswith("'")):
        raise AssertionError(f"unexpected non-string literal: {literal!r}")
    return s[1:-1].replace("''", "'")


def _parse_seed_inserts() -> list[dict]:
    text = SEED_FILE.read_text(encoding="utf-8")
    rows: list[dict] = []
    for cols_blob, vals_blob in _INSERT_RE.findall(text):
        cols = [c.strip() for c in cols_blob.split(",")]
        vals = _split_sql_values(vals_blob)
        assert len(cols) == len(vals), (
            f"column/value count mismatch: cols={cols!r} vals={vals!r}"
        )
        rows.append(dict(zip(cols, vals)))
    return rows


# ── Migration files exist and contain expected statements ──────────────


def test_migration_files_exist():
    assert SCHEMA_FILE.is_file()
    assert SEED_FILE.is_file()
    assert RATIONALE_SCHEMA_FILE.is_file()
    assert BACKFILL_FILE.is_file()


def test_003_adds_both_columns_idempotently():
    sql = RATIONALE_SCHEMA_FILE.read_text(encoding="utf-8")
    # Idempotent guard — must use IF NOT EXISTS so re-running is safe.
    assert "ADD COLUMN IF NOT EXISTS why_it_matters" in sql
    assert "ADD COLUMN IF NOT EXISTS what_pass_looks_like" in sql


def test_004_backfill_is_idempotent():
    """Each UPDATE must be guarded by `WHERE why_it_matters IS NULL` so
    re-running after a successful seed is a no-op (and doesn't clobber any
    edits a consultant made via the Settings UI)."""
    sql = BACKFILL_FILE.read_text(encoding="utf-8")
    update_count = sql.count("UPDATE public.framework_items")
    guard_count = sql.count("AND why_it_matters IS NULL")
    assert update_count == EXPECTED_ITEM_COUNT
    assert guard_count == update_count, (
        f"every UPDATE must include the IS NULL guard "
        f"({update_count} updates, {guard_count} guards)"
    )


# ── Seed file structural properties ────────────────────────────────────


def test_seed_has_expected_item_count():
    rows = _parse_seed_inserts()
    assert len(rows) == EXPECTED_ITEM_COUNT


def test_seed_inserts_use_extended_column_list():
    """All framework_items INSERTs must include the new rationale columns —
    a stray legacy 5-column INSERT would crash the seed because the columns
    now exist (003 has run by then) but no value would be supplied."""
    rows = _parse_seed_inserts()
    for r in rows:
        assert "why_it_matters" in r, "INSERT missing why_it_matters column"
        assert "what_pass_looks_like" in r, "INSERT missing what_pass_looks_like column"


def test_every_seeded_item_has_non_null_rationale():
    rows = _parse_seed_inserts()
    missing = []
    for r in rows:
        why = _unquote(r["why_it_matters"])
        pass_ = _unquote(r["what_pass_looks_like"])
        if not why or not pass_:
            missing.append(_unquote(r["id"]))
    assert not missing, (
        f"items missing rationale (why or pass): {missing}"
    )


def test_rationale_values_fit_200_chars():
    rows = _parse_seed_inserts()
    too_long: list[tuple[str, str, int]] = []
    for r in rows:
        item_id = _unquote(r["id"]) or "?"
        for field in ("why_it_matters", "what_pass_looks_like"):
            value = _unquote(r[field]) or ""
            if len(value) > MAX_RATIONALE_CHARS:
                too_long.append((item_id, field, len(value)))
    assert not too_long, (
        f"rationale fields exceed {MAX_RATIONALE_CHARS} chars: {too_long}"
    )


def test_rationale_values_are_single_sentence_no_filler():
    """Rough lint: a well-formed rationale should not contain hedging
    language. This isn't exhaustive — the human review of Phase 2 is the
    real quality gate — but it catches accidental drift toward marketing
    voice. The patterns target the verb forms specifically; the noun
    "leverage" (as in "contractual leverage") is not flagged."""
    rows = _parse_seed_inserts()
    # Each pattern is a regex matched case-insensitively against the value.
    # Verb forms only — "leverages", "leveraged", "leveraging" are filler;
    # "leverage" as a noun is fine.
    BANNED_PATTERNS = [
        r"\bit appears\b",
        r"\bit seems\b",
        r"\bbest practice\b",
        r"\brobust\b",
        r"\bleverag(?:es|ed|ing)\b",
    ]
    offenders: list[tuple[str, str, str]] = []
    for r in rows:
        item_id = _unquote(r["id"]) or "?"
        for field in ("why_it_matters", "what_pass_looks_like"):
            value = _unquote(r[field]) or ""
            for pat in BANNED_PATTERNS:
                m = re.search(pat, value, re.IGNORECASE)
                if m:
                    offenders.append((item_id, field, m.group(0)))
    assert not offenders, f"hedging / filler language detected: {offenders}"


def test_backfill_uuids_match_seed_uuids():
    """Every UUID referenced by 004 must exist in 002, otherwise the
    backfill UPDATEs will silently match zero rows after a fresh seed.
    Regression guard against typos in the UUID literals."""
    seed_ids = {_unquote(r["id"]) for r in _parse_seed_inserts()}
    backfill_text = BACKFILL_FILE.read_text(encoding="utf-8")
    backfill_ids = set(re.findall(
        r"WHERE id = '([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'",
        backfill_text,
    ))
    assert backfill_ids == seed_ids, (
        f"id sets differ — only in backfill: {backfill_ids - seed_ids}; "
        f"only in seed: {seed_ids - backfill_ids}"
    )
