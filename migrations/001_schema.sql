-- ─────────────────────────────────────────────────────────────────────
-- EA Arch Agent — schema (PostgreSQL 16). Idempotent: safe to re-apply.
-- Generated from `pg_dump --schema-only` of the live development DB.
-- Source of truth is the SQLAlchemy ORM in backend/app/models/db.py.
-- ─────────────────────────────────────────────────────────────────────

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: framework_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.framework_items (
    id character varying(36) NOT NULL,
    framework_id character varying(36) NOT NULL,
    criteria text NOT NULL,
    weight_planned double precision NOT NULL,
    sort_order integer NOT NULL
);


--
-- Name: frameworks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.frameworks (
    id character varying(36) NOT NULL,
    name character varying(200) NOT NULL,
    description text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: images; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.images (
    sha256 character varying(64) NOT NULL,
    content_type character varying(32) NOT NULL,
    bytes bytea NOT NULL,
    byte_size integer NOT NULL,
    width integer,
    height integer,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: llm_config; Type: TABLE; Schema: public; Owner: -
--
-- Singleton row (id='default') holding the user's chosen LLM model + the
-- generation knobs each Ollama call uses. Editable via Settings → LLM Model.
--

CREATE TABLE IF NOT EXISTS public.llm_config (
    id character varying(16) DEFAULT 'default'::character varying NOT NULL,
    model character varying(200) NOT NULL,
    temperature double precision DEFAULT 0.2 NOT NULL,
    num_ctx integer DEFAULT 16384 NOT NULL,
    num_predict integer DEFAULT 4096 NOT NULL,
    top_p double precision,
    top_k integer,
    repeat_penalty double precision,
    seed integer,
    keep_alive character varying(32) DEFAULT '-1'::character varying NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: prompt_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.prompt_overrides (
    key character varying(64) NOT NULL,
    template text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE IF NOT EXISTS public.sessions (
    id character varying(36) NOT NULL,
    session_type character varying(16) NOT NULL,
    mode character varying(32),
    persona character varying(32),
    focus_areas json,
    user_prompt text,
    image_hash character varying(64),
    reference_image_hash character varying(64),
    response_markdown text,
    status character varying(16) NOT NULL,
    error_message text,
    created_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    ttft_ms integer,
    total_ms integer,
    scorecards json
);


--
-- Name: framework_items framework_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'framework_items_pkey') THEN
    ALTER TABLE ONLY public.framework_items
    ADD CONSTRAINT framework_items_pkey PRIMARY KEY (id);
  END IF;
END $$;


--
-- Name: frameworks frameworks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'frameworks_pkey') THEN
    ALTER TABLE ONLY public.frameworks
    ADD CONSTRAINT frameworks_pkey PRIMARY KEY (id);
  END IF;
END $$;


--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'images_pkey') THEN
    ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (sha256);
  END IF;
END $$;


--
-- Name: llm_config llm_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'llm_config_pkey') THEN
    ALTER TABLE ONLY public.llm_config
    ADD CONSTRAINT llm_config_pkey PRIMARY KEY (id);
  END IF;
END $$;


--
-- Name: prompt_overrides prompt_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'prompt_overrides_pkey') THEN
    ALTER TABLE ONLY public.prompt_overrides
    ADD CONSTRAINT prompt_overrides_pkey PRIMARY KEY (key);
  END IF;
END $$;


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'sessions_pkey') THEN
    ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);
  END IF;
END $$;


--
-- Name: ix_framework_items_framework_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_framework_items_framework_id ON public.framework_items USING btree (framework_id);


--
-- Name: ix_sessions_session_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX IF NOT EXISTS ix_sessions_session_type ON public.sessions USING btree (session_type);


--
-- Name: framework_items framework_items_framework_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'framework_items_framework_id_fkey') THEN
    ALTER TABLE ONLY public.framework_items
    ADD CONSTRAINT framework_items_framework_id_fkey FOREIGN KEY (framework_id) REFERENCES public.frameworks(id) ON DELETE CASCADE;
  END IF;
END $$;


--
-- PostgreSQL database dump complete
--

