-- ─────────────────────────────────────────────────────────────────────
-- EA Arch Agent — seed data
--
-- Scope:
--   1. frameworks + framework_items  → TRUNCATE + INSERT
--      (canonical seed — local is the source of truth; re-running this
--      script resets the server to the snapshot below.)
--   2. prompt_overrides              → INSERT ... ON CONFLICT DO NOTHING
--      (preserves any prompt customisations a user has saved on the
--      server via Settings → Prompts; the seed only adds rows that don't
--      already exist on the target.)
--   3. llm_config                    → INSERT ... ON CONFLICT DO NOTHING
--      (preserves the server-side LLM model + sampling config the user
--      has selected via Settings → LLM Model.)
--
-- Idempotent: re-runs produce the same end state. The script is a single
-- transaction — partial application can't happen.
--
-- To regenerate this file from a current local DB:
--     pg_dump -U kpmg -d kpmg_arch --data-only --inserts --column-inserts \
--       -t frameworks -t framework_items -t prompt_overrides -t llm_config \
--       > /tmp/dump.sql
--   Then splice the INSERT blocks into the four sections below.
-- ─────────────────────────────────────────────────────────────────────

BEGIN;

-- Wipe existing rows; CASCADE handles framework_items via FK.
TRUNCATE TABLE public.framework_items, public.frameworks RESTART IDENTITY CASCADE;

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

--
-- Data for Name: frameworks; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Buisness Compliance Check', NULL, '2026-05-01 09:33:29.579259+00', '2026-05-01 09:33:29.579266+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('911e6cf6-d269-4eae-82c3-653e76268385', 'EA Compliance Check', NULL, '2026-05-01 09:33:29.638728+00', '2026-05-01 09:33:29.638733+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('a72027e3-6a14-4761-ac49-6958f7910e04', 'CX Compliance Check', NULL, '2026-05-01 09:33:29.694606+00', '2026-05-01 09:33:29.69461+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Data Compliance Check', NULL, '2026-05-01 09:33:29.746675+00', '2026-05-01 09:33:29.746681+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Application Compliance Check', NULL, '2026-05-01 09:33:29.803136+00', '2026-05-01 09:33:29.803143+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Integration Compliance Check', NULL, '2026-05-01 09:33:29.859073+00', '2026-05-01 09:33:29.85908+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('6f6b1e83-4952-4f8a-bd63-d9cf80ff83e6', 'Infrastructure Compliance Check', NULL, '2026-05-01 09:33:29.91471+00', '2026-05-01 09:33:29.914716+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('695d2c2f-1e8c-4a88-8940-71cdffbef9c3', 'Cloud Compliance Check', NULL, '2026-05-01 09:33:29.966773+00', '2026-05-01 09:33:29.966778+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Cyber security Compliance Check', NULL, '2026-05-01 09:33:30.022835+00', '2026-05-01 09:33:30.02284+00');
INSERT INTO public.frameworks (id, name, description, created_at, updated_at) VALUES ('f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Artificial Intelligence (AI) Compliance Check', NULL, '2026-05-01 09:33:30.075119+00', '2026-05-01 09:33:30.075125+00');


--
-- Data for Name: framework_items; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('65624f18-426f-4dfe-be29-02abb2a9c9d3', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q1-S-BUS-1.1:Does the solution have documented recovery objectives / failover mechanisms?', 12, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('8b733d96-62c4-4bbe-8bc5-69bc8106a8bd', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q2-S-BUS-1.1:Are high availability, redundancy, and failover mechanisms implemented to meet business continuity requirements?', 14, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('70991449-d877-45f0-9022-e30c8a390a90', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q3-S-BUS-1.1:Are backup and disaster recovery processes defined & tested?', 14, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('a5b51c1c-45e0-4ba0-a385-c4535e2681f8', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q4-S-BUS-1.1:Are backups encrypted and regularly tested to ensure recoverability in case of data loss or ransomware attacks?', 11, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('12d8833f-a8ec-4971-ae53-741a345a4af5', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q5-S-BUS-1.2:Are vendor-provided SLAs and support models aligned with NCGR''s expectations?', 10, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('bb3a12fd-162b-4460-ad4f-d06cc1d2112d', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q6-S-BUS-2.1:Are remote access controls (e.g. MFA/VPN/Zero Trust) and aligned with NCGR IAM policy? Provide evidence (access model / policy).', 15, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('82160faf-9c21-4911-9e53-802e3b2443ac', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q7-S-BUS-3.1:Are As-Is/To-Be processes documented (BPMN) and linked to automation tools/requirements (e.g. in iServer if applicable)?', 12, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('66e7c65c-87d2-450b-80c6-a56be69f5308', '0f76e9f7-8df3-4612-a9c9-6627856e4514', 'Q8-S-BUS-3.2:Provide standardized process documentation used (notation, templates, repository) along with change approvals for process changes (preferably automated).', 12, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('692bfcac-f57d-46f8-b905-22b305cee89a', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q1-S-EA-1.1: Is the initiative traceable to approved business outcomes and KPIs?', 12, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('78d1c0e0-6dd8-42db-8d3e-f4bd35959d9d', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q2-S-EA-1.1: Is there a documented TCO, cost, licensing approach, and long-term sustainability for the proposed solution?', 8, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('d48e9510-db3a-4e33-aafd-8f6865a76bd1', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q3-S-EA-1.2: Have existing NCGR platforms/services APIs been assessed for reuse, and is any duplication justified and approved?', 11, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('b42b74de-54c5-4aff-b9ee-29e22a903c7c', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q4-S-EA-1.1: Is the initiative aligned with NCGR strategic execution roadmaps (provide mapping to roadmap items)?', 12, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('ee01eb8a-a7ec-4181-a10f-c9f9faef7fba', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q5-S-EA-3.1: Does the solution comply with applicable Saudi regulatory requirements (e.g., NCA) and relevant EA standards (e.g., TOGAF, NDRA)?', 20, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('8287fc28-5b0b-4d65-805b-73e476e29a7a', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q6-S-EA-3.2: Is there any deviation from the standard technology stack at NCGR?', 15, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('f8dc9559-a24b-496d-9ab4-512a115e27dc', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q7-S-EA-4.1: For initiatives using emerging technology, was the solution reviewed through EA governance and approved before implementation (provide evidence)?', 7, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('0e013210-798d-4d88-9ba6-b6be1d172e36', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q8-S-EA-5.1: Provide evidence of emerging technology maturity & risk assessment + readiness (support/security) for adoption.', 5, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('26b33c2f-f05d-4387-8823-d27d66733fcc', '911e6cf6-d269-4eae-82c3-653e76268385', 'Q9-S-EA-6.1: Has the technical debt been assessed for risk and business impact, and formally accepted by the accountable owner?', 10, 8);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('a4cece84-8d02-4f2b-a32e-133f619c4a57', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q1-S-CX-1.1: Are customer journeys documented and validated, including key points?', 16, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('780ec515-0425-4db9-ab08-c132d374966d', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q2-S-CX-1.1: Are measurable customer and business outcomes defined for the initiative and linked to NCGR strategic objectives?', 18, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('96b8eb54-1469-4b5c-95a0-350b08aac331', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q3-S-CX-1.1: For a user-centric experience, are accessibility and ease-of-use criteria considered?', 14, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('84fa80f6-d37b-455e-a9f7-ecb679aea76e', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q4-S-CX-2.1: Does the solution provide self-service capabilities for end users where applicable?', 12, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('6a76fc73-628d-4c1f-a13d-7af0d04d54a3', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q5-S-CX-2.2: Is customer data, context, and journey progress shared consistently across all channels (web, mobile), with evidence of synchronization/integration?', 16, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('ce84a7bc-2150-4b20-899e-d49d34698221', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q6-S-CX-3.1: Is feedback/analytics embedded and linked to journeys/steps/personas?', 12, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('2baf91a0-383a-40d7-8f46-8fc51b928f38', 'a72027e3-6a14-4761-ac49-6958f7910e04', 'Q7-S-CX-3.2: Are front-end, journey logic, and back-end services decoupled for rapid change management?', 12, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('3c85f6f2-6b09-43d8-8d31-9c93a540f94f', '6f6b1e83-4952-4f8a-bd63-d9cf80ff83e6', 'Q1-S-INF-1.1: Does the infrastructure design meet NCGR''s approved standards for servers, networking, and virtualization?', 25, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('f961ab9b-c981-467c-9581-79ee71b8ac60', '6f6b1e83-4952-4f8a-bd63-d9cf80ff83e6', 'Q2-S-INF-1.2: Are the proposed technologies compatible with the current technology stack in NCGR?', 20, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('4c13a656-fdbc-477a-83bb-441d498cb858', '6f6b1e83-4952-4f8a-bd63-d9cf80ff83e6', 'Q3-S-INF-1.3: Does the RFP clearly define integration requirements with existing systems and data flows?', 15, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('0cc5587a-87aa-4039-be79-c8ebf8bf488d', '6f6b1e83-4952-4f8a-bd63-d9cf80ff83e6', 'Q4-S-INF-2.1: Is the infrastructure and cloud design independent of specific vendors or proprietary technologies, allowing portability and flexibility across different platforms and environments?', 15, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('92f687cf-5643-4203-ab1e-e938d4beddd9', '6f6b1e83-4952-4f8a-bd63-d9cf80ff83e6', 'Q5-S-INF-3.1: Is the network segment (zones/DMZ/as applicable) with redundancy/failover to maintain continuity?', 25, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('06ac79fe-d6ee-4882-ad8b-5ed299d5349f', '695d2c2f-1e8c-4a88-8940-71cdffbef9c3', 'Q1-S-CLD-1.1: Is cloud assessed, and is the selected deployment model (cloud/hybrid/on-prem) aligned with NCGR cloud strategy and justified where needed?', 30, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('8a1546dc-d170-450e-b757-d7bb56a03642', '695d2c2f-1e8c-4a88-8940-71cdffbef9c3', 'Q2-S-CLD-1.2: Is the cloud design portable (minimizes CSP lock-in) with a defined migration/exit approach if needed?', 25, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('3902f44a-7ea2-4b5c-86fa-100b0c98b94d', '695d2c2f-1e8c-4a88-8940-71cdffbef9c3', 'Q3-S-CLD-2.1: Is the shared responsibility model clearly defined, documented, and agreed between NCGR and the CSP?', 20, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('9d001ceb-5aad-4f34-abc5-ab4b8ee187e4', '695d2c2f-1e8c-4a88-8940-71cdffbef9c3', 'Q4-S-CLD-2.2: Does the infrastructure support monitoring, logging, and alerting for performance/capacity/security events?', 25, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('62aad710-8c5c-4997-bd2d-1c8b7e0ecdff', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q1-S-AI-1.1: Is an ethical impact assessment completed and formally approved before deployment or any material change?', 14, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('101480b8-26d3-44b3-9dfa-b52284ca33ce', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q2-S-AI-1.2: For AI system supporting high-impact or rights-affecting decisions, are documented, human-understandable explanations of system', 10, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('940f414b-7657-4acb-93b6-fcfc54bc26f2', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q3-S-AI-1.3: Has bias testing been completed, and have identified biases been mitigated and approved before deployment?', 12, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('955e2de6-ef00-4e40-a14d-2a7e44b4d104', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q4-S-AI-1.4: Is there a documented business/technical owner and accountable authority for the AI system before operation?', 8, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('529a6289-f462-49e4-99c4-795dfe863b8e', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q5-S-AI-2.1: Is the AI system riskimpact-classified, with defined human oversight for critical decisions, and are audit records maintained for outputs, interventions, and final decisions?', 14, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('39c7650b-a19a-4945-96b0-473dd2c7fe9e', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q6-S-AI-2.2: Does the AI solution provided by the vendor include documented governance, risk, and compliance artifacts? Were this requirements added to the RFP?', 8, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('384e1eea-348e-426a-ae13-c3e81ce11741', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q7-S-AI-3.1: Is the data used for AI classified, validated, and formally approved for training and operation, in compliance with privacy and ethical', 12, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('de33b0dc-b524-46e7-9881-fbdf89ddf492', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q8-S-AI-3.2: Is the AI model continuously monitored (performance, drift, impact) using defined metrics, and if issues or requirement changes arise, is it reviewed and appropriately updated/retrained/retired?', 12, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('02cb740c-8ba6-43e0-8785-7558ff233a3f', 'f8d0dbd8-f264-4c78-97ca-2eae1f2e66fc', 'Q9-S-AI-3.3: Is documentation maintained for all AI lifecycle stages, including data usage, training, deployment, monitoring, and decommissioning?', 10, 8);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('bdd778c9-496f-4a3a-a85f-ae049ae331cd', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-1.1: All user devices explicitly authenticated and authorized, with continuous verification where applicable?', 8, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('35d849f9-5781-4519-9069-5719cb686371', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-1.2: Access controls implemented according to the principle of least privilege for all users and systems?', 10, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('a77778a1-699d-4c1f-88fe-9e76395f2313', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-1.3: SSO and MFA enforced for all internal users in line with NGCSRA requirements?', 10, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('c7fac74b-9e8e-41c8-a391-0134ba1129b9', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-1.4: Is logging and monitoring for all critical events, with alerts for suspicious activity?', 9, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('7dae69d6-e694-4c7b-ace1-013c9aba8dd4', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2: Network security controls implemented (DMZ as applicable, firewalls, and intrusion detection/prevention) to prevent unauthorized access and lateral movement?', 10, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('02c7a720-8bd3-43aa-8725-ef7666859902', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2.2: Third-party integrations and APIs secured and validated against NGCSRA security standards?', 9, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('bd45b61e-240a-4c27-8eb8-2ba39116c1ae', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2.3: Third-party vendor integrations risk-assessed and approved, with ongoing security monitoring throughout the lifecycle?', 8, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('abeba7bc-c7c5-4218-848b-b70e8045405d', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2.4: Does the solution apply security-by-design principles (e.g. authentication, authorization, encryption, secure APIs)?', 10, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('d9b630c2-c805-4c43-bd01-2445fb68ffff', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2.5: Security, compliance, and data privacy requirements explicitly defined and achievable?', 8, 8);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('153f5865-3dfb-4d6a-a55b-549f569af529', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2.6: Security patches and updates applied in a timely manner according to NGCSRA policies?', 9, 9);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('ca48147b-fe7a-4649-b6e8-c11d416ae49f', '875947f1-0e8a-46ab-a958-ae3e56c8bdce', 'Q1-S-YB-2.7: Is there a process for incident response and recovery in case of a security breach?', 9, 10);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('db0e41c8-dc57-4338-b06d-1323fc1b9ead', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q1-S-INT-1.1: Does the solution integrate with NCGR/external systems using approved and standardized mechanisms (APIs, event-driven, messaging), aligned with NCGR integration', 16, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('b34ebae4-781c-4063-9482-158c37e4e70a', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q2-S-INT-1.2: Are the integration flows implemented using configuration-based approaches (rather than hard-coded/custom scripts) to ensure maintainability and easier updates?', 8, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('540836a7-7b75-4b00-9cc4-e46edbfe6b99', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q3-S-INT-1.3: Is the integration approach compatible with decision tree mentioned in NCGR guidelines document?', 8, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('23285e46-50ba-4de2-86e9-bafa33cb3076', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q4-S-INT-1.4: Does the integration design allow for monitoring, logging, and alerting of interface failures or delays?', 9, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('10e1f598-ac2f-4e5a-aa8e-f565714c9f3a', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q5-S-INT-1.5: Are integration points tested for performance, reliability, and error handling before deployment?', 13, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('43d813f4-15a6-4735-8825-ba9a8953c9cb', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q6-S-INT-1.6: Are APIs used in the solution deployed on multiple servers instances to ensure high availability?', 8, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('7b430eab-b651-420e-9c21-ae7814cbcc17', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q7-S-INT-1.7: Does the integration architecture provide automatic failover or the ability to switch to a disaster recovery site in case of middleware or message broker failures?', 13, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('9f904eac-a09a-4d18-8f87-d8e00182b7d8', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q8-S-INT-1.8: Are APIs used in the solution deployed on multiple servers instances to ensure high availability?', 6, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('26cbec69-ac18-4fd5-9adb-fd5811dbc66b', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q9-S-INT-1.9: Is the integration solution documented as aligned with approved NCGR integration platforms and standards?', 8, 8);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('a5983bfb-82ad-42b7-9100-4b9bea2af452', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q10-S-INT-1.10: Does the solution use DataPower for internal communication and APIGW for external communication?', 6, 9);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('6963e7ef-2c83-4dbe-8807-74eed63f8cb0', 'ea9e274f-c014-4297-8b5d-41c825b00b5a', 'Q11-S-INT-1.11: In case of connecting to FileNet or any other similar solution related to file management, does the solution utilize file transfer solutions in NCGR such as IBM MFT?', 5, 10);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('3530e189-12cb-4a8b-827c-4d1fb7872816', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q1-S-APP-1.1: Has reuse of existing solutions considered first? / Was a COTS solution evaluated before custom development?', 7, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('74d366f4-dff2-49eb-a3d2-8c1e4c4c576b', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q2-S-APP-1.2: Can the solution be used by other units in NCGR, not just a single unit?', 5, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('2426e09e-3e77-4e7b-b671-2c36c0a14440', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q3-S-APP-2.1: Does the solution minimize vendor lock-in and ensure portability across environments or platforms?', 6, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('8c019200-8e61-4b6c-8f9c-2145d5ef7435', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q4-S-APP-2.2: Is the technology stack aligned with NCGR''s approved technology stack?', 8, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('b347f70a-cb2d-440e-9fe3-7cd448b58cfa', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q5-S-APP-3.1: Does the RFP allow for modularity, reusability, and maintainability of components?', 5, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('df7ffcf2-4f5e-40e9-beb4-0668a44f8780', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q6-S-APP-3.1: Is the solution designed in a modular way that facilitates maintenance and controlled updates without impacting the entire system?', 7, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('c87e7de3-df92-438e-9440-f8ffaf58a258', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q7-S-APP-3.2: Are key operational tasks automated where feasible (e.g., deployments, scheduled jobs, monitoring tasks, user provisioning)?', 4, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('4e371d49-72b6-4c80-9f4f-1c7b8408a861', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q8-S-APP-3.3: Is operational documentation available and has knowledge transfer completed (or planned) for ongoing support?', 4, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('748debbd-a6a2-4809-a517-e0a5f72a6186', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q9-S-APP-4.1: Is the solution loosely coupled, enabling incremental changes without impacting other components?', 6, 8);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('ea7b4466-d8e2-4bbe-b821-9cc488722286', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q10-S-APP-5.1: Is the solution designed using a layered architecture that separates presentation, business logic, and data layers?', 6, 9);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('153069ca-b4d1-49e5-938e-e5699de0cbca', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q11-S-APP-6.1: Is the selected solution the best-fit with minimal customization, and is any customization justified and formally approved (provide rationale/impact + approval)', 5, 10);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('5fc6fc1e-a554-489a-85f8-88972c756ff1', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q12-S-APP-7.1: Can the application scale horizontally or vertically to handle increased workloads without major redesign?', 6, 11);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('fb738cdc-fa0b-4bde-b03e-57c029366771', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q13-S-APP-7.2: Is the infrastructure scalable to handle expected growth in workloads and users without major redesign?', 5, 12);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('9294fbe1-ac3a-40dc-b650-94f15f24b8f9', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q14-S-APP-7.2: Are resource utilization and performance optimized to reduce costs?', 4, 13);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('da6bc1df-a291-4a37-a8cb-63c180a978fc', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q15-S-APP-8.1: Does the architecture include mechanisms for high availability, failover, and disaster recovery?', 6, 14);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('58046539-4958-4b84-947b-6b6d4ca3d7e4', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q16-S-APP-8.1: Are scalability, performance, and availability requirements addressed in the RFP?', 4, 15);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('aa29e6db-72ab-4b7b-a5c7-994f35ca8ae5', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q17-S-APP-8.2: Provide evidence that resilience and security controls are incorporated early in the solution design to avoid single points of failure.', 6, 16);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('2d44fc99-c1a8-4269-b34b-cde0b1fc721f', 'cad90d1f-1a57-4e28-ae05-164d06a0d9e2', 'Q18-S-APP-9.1&9.2: Are audit logs for critical actions/events captured with sufficient details, protected from tampering, and retained for the defined period in accordance with applicable policies?', 6, 17);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('9adacf71-9346-47ed-bed4-d878c3c20da3', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q1-S-DAT-1.1: Is there a documented enterprise data model (conceptual, logical, and physical) aligned with business domains?', 8, 0);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('b34eed02-c9c0-4e52-bc3a-f0a270f2a9bd', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q2-S-DAT-1.2: Is there a defined governance framework in place (roles, ownership, and stewardship)?', 10, 1);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('d4c525a3-e6ad-42c3-8e1f-777d2db6f6a3', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q3-S-DAT-2.1: Are data classification levels defined and enforced according to sensitivity and compliance requirements (e.g., personal data, financial data)?', 9, 2);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('a8d3ff70-48b6-4b8e-9ceb-51ba9da5f4ff', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q4-S-DAT-2.2: Are there policies for data retention, archival, and disposal aligned with regulatory procedures at NCGR and with business needs?', 8, 3);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('84d06ebf-49b6-4735-aba4-9b28fe577a7d', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q5-S-DAT-2.3: Is access to sensitive NCGR data granted based on documented approval and data classification, using standardized and controlled access mechanisms?', 12, 4);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('4cd7f144-9f52-4c01-bc03-0c40669854fc', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q6-S-DAT-3.1: Are there automated processes or tools to monitor and improve data quality (accuracy, completeness, timeliness)?', 9, 5);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('5f9f809d-dd01-441d-8d85-c532e6a0c236', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q7-S-DAT-3.2: Are data exchange/integration methods (APIs, ETL/ELT, messaging) implemented according to approved patterns/standards and designed to ensure data quality, integrity during movement?', 10, 6);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('765ef90c-18dd-42be-8443-44e8db1604ee', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q8-S-DAT-3.3: For key datasets, is high-level data lineage documented (as applicable)?', 7, 7);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('fe8bbf25-192f-426f-af9e-5edbd8cbb5a2', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q9-S-DAT-4.1.4: Does the solution use standardized KPI definitions and approved datasets/schemas to ensure consistent BI reporting, interpretation and avoid unmanaged shadow analytics?', 7, 8);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('4acaf6cd-7fa2-41d6-98a6-80dde44847c2', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q10-S-DAT-5.1: Are all sensitive data at rest and in transit encrypted using approved cryptographic standards?', 15, 9);
INSERT INTO public.framework_items (id, framework_id, criteria, weight_planned, sort_order) VALUES ('56e70b7f-ad52-4e82-ba68-90dc582ba425', '45e9ab66-e14d-4219-9168-b187e2fd66f0', 'Q11-S-DAT-5.2: If encryption is not applied, provide the approved exception and justification.', 5, 10);


--
-- PostgreSQL database dump complete (frameworks + framework_items)
--


--
-- Data for Name: prompt_overrides; Type: TABLE DATA; Schema: public; Owner: -
--
-- Non-destructive seed: existing server rows are preserved (ON CONFLICT
-- DO NOTHING). To force-overwrite a saved prompt, delete it first via
-- the UI (Settings → Prompts → Reset to default) or:
--     DELETE FROM prompt_overrides WHERE key = 'analyze_compliance';
-- Then re-run this script.

-- (No prompt overrides in the source dump.)
-- Example INSERT shape, kept here for the regenerator step (see header):
--   INSERT INTO public.prompt_overrides (key, template, updated_at)
--   VALUES ('analyze_compliance', '<full template text>', NOW())
--   ON CONFLICT (key) DO NOTHING;


--
-- Data for Name: llm_config; Type: TABLE DATA; Schema: public; Owner: -
--
-- Singleton row (id='default'). Non-destructive seed for the same reason
-- as prompt_overrides — preserves whatever the server-side user has
-- chosen via Settings → LLM Model.

-- (No llm_config row in the source dump.)
-- Example INSERT shape:
--   INSERT INTO public.llm_config (
--       id, model, temperature, num_ctx, num_predict,
--       top_p, top_k, repeat_penalty, seed, keep_alive, updated_at
--   ) VALUES (
--       'default', 'qwen2.5vl:7b', 0.2, 16384, 4096,
--       NULL, NULL, NULL, NULL, '-1', NOW()
--   )
--   ON CONFLICT (id) DO NOTHING;


COMMIT;
