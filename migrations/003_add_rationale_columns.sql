-- ─────────────────────────────────────────────────────────────────────
-- EA Arch Agent — schema migration 003: add per-criterion rationale.
-- Idempotent: safe to re-apply (uses ALTER TABLE … ADD COLUMN IF NOT EXISTS).
--
-- Two short fields per criterion that the per-criterion compliance prompt
-- (compliance_per_criterion_v2) injects between the criterion text and
-- the document body, so the model scores against intent (the risk being
-- addressed, the evidence that constitutes a pass) rather than the
-- criterion text alone.
--
-- NULL is permitted — older / user-created criteria without rationale
-- still render cleanly because the prompt builder skips empty lines.
-- ─────────────────────────────────────────────────────────────────────

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: framework_items.why_it_matters; Type: COLUMN; Schema: public; Owner: -
--
-- One sentence (<=200 chars) naming the risk, harm, or failure mode the
-- criterion protects against. Surfaced verbatim in the per-criterion
-- prompt as `Why this matters: …`.
--

ALTER TABLE IF EXISTS public.framework_items
    ADD COLUMN IF NOT EXISTS why_it_matters text;

--
-- Name: framework_items.what_pass_looks_like; Type: COLUMN; Schema: public; Owner: -
--
-- One sentence (<=200 chars) naming the concrete artefact / control /
-- document that constitutes a pass. Surfaced verbatim as
-- `What a pass looks like: …`.
--

ALTER TABLE IF EXISTS public.framework_items
    ADD COLUMN IF NOT EXISTS what_pass_looks_like text;

--
-- Migration 003 complete.
--
