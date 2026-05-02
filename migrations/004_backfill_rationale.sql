-- ─────────────────────────────────────────────────────────────────────
-- EA Arch Agent — data migration 004: backfill rationale for the 93
-- seeded framework_items rows.
--
-- No-op when 002_seed_data.sql is up to date (which is the normal flow,
-- because 002 TRUNCATE-and-INSERTs with the rationale baked in). This
-- migration is the safety net for partial-migration scenarios where an
-- operator applied 003 to a populated DB without re-seeding.
--
-- Idempotent: every UPDATE is guarded by `WHERE why_it_matters IS NULL`
-- so an item that already has rationale is left untouched (preserves any
-- user edits made via the Settings UI).
--
-- Content rules per row:
--   • One sentence, ≤200 chars per field.
--   • why_it_matters: names the risk / harm / failure mode the criterion
--     guards against.
--   • what_pass_looks_like: names the concrete artefact / control /
--     document that constitutes a pass, KSA-anchored where applicable
--     (SDAIA, PDPL, NDMO, NCA, NGCSRA, TOGAF, NDRA).
-- ─────────────────────────────────────────────────────────────────────

BEGIN;


-- ── Buisness Compliance Check ────────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Without RTO/RPO targets, recovery is improvised and the business cannot quantify outage cost or measure whether the disaster recovery plan meets continuity needs.',
       what_pass_looks_like = 'A signed BCM plan stating RTO, RPO, and failover trigger criteria per service, dated within the last review cycle.'
 WHERE id = '65624f18-426f-4dfe-be29-02abb2a9c9d3'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Single points of failure cause cascading outages that breach SLA commitments and erode customer trust during the recovery window.',
       what_pass_looks_like = 'An architecture diagram showing redundant active/active or active/passive components per tier with a tested automatic failover runbook.'
 WHERE id = '8b733d96-62c4-4bbe-8bc5-69bc8106a8bd'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Untested backups routinely fail to restore under real conditions, turning a recoverable incident into permanent data loss.',
       what_pass_looks_like = 'A backup policy plus dated restore-test reports proving recovery within RTO from production-grade backups within the last 12 months.'
 WHERE id = '70991449-d877-45f0-9022-e30c8a390a90'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unencrypted backups become the attacker''s exfiltration target; untested backups fail silently when ransomware demands a clean restore.',
       what_pass_looks_like = 'Backup configuration showing AES-256 at rest and in transit, plus an immutable / air-gapped copy with a restore test signed off by IT operations.'
 WHERE id = 'a5b51c1c-45e0-4ba0-a385-c4535e2681f8'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Misaligned vendor SLAs leave critical services unsupported during incidents, with NCGR carrying the operational risk it thought it had transferred.',
       what_pass_looks_like = 'A vendor contract clause matrix showing response time, resolution time, and uptime commitments meeting or exceeding NCGR''s documented SLA targets.'
 WHERE id = '12d8833f-a8ec-4971-ae53-741a345a4af5'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Weak remote access — shared accounts, stale VPN credentials, missing MFA — is the dominant entry vector for attackers targeting government environments.',
       what_pass_looks_like = 'An access-control design citing NCGR IAM policy with MFA, VPN or Zero Trust enforcement, and a per-role access matrix approved by the security team.'
 WHERE id = 'bb3a12fd-162b-4460-ad4f-d06cc1d2112d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Undocumented processes block process automation, audit, and handoff to operations, locking institutional knowledge in individuals.',
       what_pass_looks_like = 'BPMN diagrams for As-Is and To-Be flows stored in iServer (or equivalent) with explicit links to the automation tools or requirements that implement them.'
 WHERE id = '82160faf-9c21-4911-9e53-802e3b2443ac'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Ad-hoc process documentation makes change impact unreviewable and leaves auditors unable to trace who approved what and when.',
       what_pass_looks_like = 'A process-documentation standard (notation, template, repository) plus a change-approval workflow with automated routing and a logged audit trail.'
 WHERE id = '66e7c65c-87d2-450b-80c6-a56be69f5308'
   AND why_it_matters IS NULL;


-- ── EA Compliance Check ──────────────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Initiatives without measurable business outcomes consume budget without proving value and cannot be evaluated against NCGR''s strategic portfolio.',
       what_pass_looks_like = 'A traceability matrix linking each initiative scope item to a named business outcome and a quantified KPI baseline, signed by the business sponsor.'
 WHERE id = '692bfcac-f57d-46f8-b905-22b305cee89a'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Hidden licensing costs and unsustainable run-rate models surface mid-build, forcing scope cuts or unbudgeted spend that derail multi-year roadmaps.',
       what_pass_looks_like = 'A TCO model covering build and 3-year run costs, licensing terms, and renewal pathway, reviewed by procurement and finance before contract award.'
 WHERE id = '78d1c0e0-6dd8-42db-8d3e-f4bd35959d9d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Duplicate platforms fragment data, duplicate operating costs, and increase the integration surface area NCGR must maintain.',
       what_pass_looks_like = 'A reuse-assessment register listing existing NCGR platforms / APIs evaluated, the reuse decision for each, and approval rationale for any new build.'
 WHERE id = 'd48e9510-db3a-4e33-aafd-8f6865a76bd1'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Off-roadmap initiatives compete for the same scarce delivery capacity and dilute the prioritised strategic outcomes the roadmap was designed to deliver.',
       what_pass_looks_like = 'An explicit mapping table showing each initiative deliverable against the NCGR strategic roadmap item it advances, dated and signed by EA.'
 WHERE id = 'b42b74de-54c5-4aff-b9ee-29e22a903c7c'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Non-compliance with NCA, NDRA, or TOGAF baselines exposes NCGR to regulator findings and forces costly redesign once auditors flag the gap.',
       what_pass_looks_like = 'A compliance matrix mapping the design to applicable NCA, NDRA, and TOGAF requirements with evidence cells citing the design artefact that satisfies each.'
 WHERE id = 'ee01eb8a-a7ec-4181-a10f-c9f9faef7fba'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unjustified stack deviations create operational silos, training gaps, and licensing surprises that the standardised stack was deliberately designed to avoid.',
       what_pass_looks_like = 'A deviation register naming the standard component bypassed, the technical or business rationale, and EA-board approval before build.'
 WHERE id = '8287fc28-5b0b-4d65-805b-73e476e29a7a'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Emerging tech adopted without governance bypasses risk, security, and supportability checks, leaving NCGR with prototypes that cannot graduate to production.',
       what_pass_looks_like = 'An EA governance minute or decision log approving the emerging-technology selection, dated before the implementation milestone.'
 WHERE id = 'f8dc9559-a24b-496d-9ab4-512a115e27dc'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Immature emerging-tech in production breaks unpredictably and lacks vendor support; without a maturity / readiness review the operational owner inherits the risk blind.',
       what_pass_looks_like = 'A maturity and readiness assessment covering vendor stability, security posture, support model, and exit options, signed by both EA and operations.'
 WHERE id = '0e013210-798d-4d88-9ba6-b6be1d172e36'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unaccepted technical debt accrues interest invisibly, eventually forcing emergency rework that displaces planned roadmap work.',
       what_pass_looks_like = 'A technical-debt register with risk and business-impact scoring per item, plus a formal acceptance signature from the accountable owner.'
 WHERE id = '26b33c2f-f05d-4387-8823-d27d66733fcc'
   AND why_it_matters IS NULL;


-- ── CX Compliance Check ──────────────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Unvalidated journey assumptions produce experiences that fail at the moments customers actually care about, surfacing only after launch through complaints.',
       what_pass_looks_like = 'Journey maps per persona covering key touchpoints, validated through customer research with research-method evidence and dated sign-off.'
 WHERE id = 'a4cece84-8d02-4f2b-a32e-133f619c4a57'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Initiatives without explicit outcome linkage cannot be prioritised against NCGR strategy or measured for actual customer impact post-launch.',
       what_pass_looks_like = 'An outcomes register mapping each initiative to a named NCGR strategic objective with measurable customer and business outcome targets.'
 WHERE id = '780ec515-0425-4db9-ab08-c132d374966d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Ignoring accessibility excludes citizens with disabilities and breaches KSA accessibility commitments alongside WCAG 2.1 AA expectations.',
       what_pass_looks_like = 'Accessibility acceptance criteria citing WCAG 2.1 AA tied to test cases, plus a documented ease-of-use review with usability metrics.'
 WHERE id = '96b8eb54-1469-4b5c-95a0-350b08aac331'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Missing self-service drives every routine request to call centres, inflating cost-to-serve and creating long resolution windows for tasks the user could complete unaided.',
       what_pass_looks_like = 'A self-service capability list per journey with measurable adoption / containment targets and the channels (web, mobile, kiosk) supported.'
 WHERE id = '84fa80f6-d37b-455e-a9f7-ecb679aea76e'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unshared journey state forces customers to restart from zero on every channel switch, eroding trust and inflating handle times for live agents.',
       what_pass_looks_like = 'An integration design showing journey-state synchronisation across web, mobile, and contact-centre channels backed by a shared customer-context store.'
 WHERE id = '6a76fc73-628d-4c1f-a13d-7af0d04d54a3'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Analytics divorced from journey context cannot tell product owners which step is failing, leaving improvement decisions to opinion rather than evidence.',
       what_pass_looks_like = 'A feedback-instrumentation plan tagging each journey step with a measurable event, plus a dashboard segmented by persona and journey stage.'
 WHERE id = 'ce84a7bc-2150-4b20-899e-d49d34698221'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Tightly coupled front-end and back-end forces a full-stack release for every cosmetic change, blocking the rapid iteration CX teams need.',
       what_pass_looks_like = 'An architecture diagram with explicit interface contracts (APIs, event streams) separating presentation, journey orchestration, and back-end services.'
 WHERE id = '2baf91a0-383a-40d7-8f46-8fc51b928f38'
   AND why_it_matters IS NULL;


-- ── Infrastructure Compliance Check ──────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Off-standard infrastructure choices fragment operational tooling and prevent reuse of NCGR''s tested patterns for monitoring, patching, and recovery.',
       what_pass_looks_like = 'A conformance matrix mapping the infrastructure design to NCGR''s approved server, network, and virtualisation standards with deviations explicitly EA-approved.'
 WHERE id = '3c85f6f2-6b09-43d8-8d31-9c93a540f94f'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Incompatible technologies create integration friction and require duplicate operational expertise NCGR must hire or train for indefinitely.',
       what_pass_looks_like = 'A compatibility assessment listing each new technology against the existing NCGR stack with integration patterns and operational handover documented.'
 WHERE id = 'f961ab9b-c981-467c-9581-79ee71b8ac60'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Vague RFP integration requirements get bids missing the integrations NCGR depends on, surfacing as scope changes after contract signature.',
       what_pass_looks_like = 'An RFP integration section listing each upstream / downstream system, the required data flow, and acceptance criteria for each integration point.'
 WHERE id = '4c13a656-fdbc-477a-83bb-441d498cb858'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Vendor-locked designs prevent migration, repricing, and disaster-recovery options that a portable design would preserve as risk mitigation.',
       what_pass_looks_like = 'An architecture decision record citing portable abstractions (containers, open APIs, IaC) and a documented exit / migration path off each proprietary component.'
 WHERE id = '0cc5587a-87aa-4039-be79-c8ebf8bf488d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Flat networks without segmentation let lateral movement and single-link failures take down the whole environment in one step.',
       what_pass_looks_like = 'A network design showing zones / DMZ as applicable, redundant links per critical path, and tested failover behaviour with documented RTO.'
 WHERE id = '92f687cf-5643-4203-ab1e-e938d4beddd9'
   AND why_it_matters IS NULL;


-- ── Cloud Compliance Check ───────────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Cloud / hybrid / on-prem decisions made without strategy alignment create stranded workloads and diverging operational models the cloud team cannot support.',
       what_pass_looks_like = 'A deployment-model decision document citing NCGR cloud strategy and NCA cloud cybersecurity controls, with justification per workload.'
 WHERE id = '06ac79fe-d6ee-4882-ad8b-5ed299d5349f'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'CSP lock-in turns commercial renegotiation into a forced migration with months of rework, undermining NCGR''s bargaining position.',
       what_pass_looks_like = 'An architecture decision record citing portable services (containers, open standards) plus a documented exit approach with migration steps and effort estimate.'
 WHERE id = '8a1546dc-d170-450e-b757-d7bb56a03642'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Ambiguous shared-responsibility leaves security and recovery tasks unowned between NCGR and CSP, surfacing only when an incident lands in the gap.',
       what_pass_looks_like = 'A signed shared-responsibility matrix per service naming NCGR vs CSP ownership for security, backup, monitoring, patching, and incident response.'
 WHERE id = '3902f44a-7ea2-4b5c-86fa-100b0c98b94d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Cloud infrastructure without observability hides capacity, performance, and security events until they become customer-visible incidents.',
       what_pass_looks_like = 'An observability design covering performance, capacity, and security event logging, with thresholds and alert routes documented in the operations runbook.'
 WHERE id = '9d001ceb-5aad-4f34-abc5-ab4b8ee187e4'
   AND why_it_matters IS NULL;


-- ── Artificial Intelligence (AI) Compliance Check ────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Without an EIA, biases, fairness gaps, and rights-affecting harms surface in production where remediation is expensive and may breach SDAIA AI ethics obligations.',
       what_pass_looks_like = 'A signed Ethical Impact Assessment per SDAIA AI Ethics Principles, dated before go-live, with approval signature from the AI governance committee or accountable authority.'
 WHERE id = '62aad710-8c5c-4997-bd2d-1c8b7e0ecdff'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Opaque rights-affecting AI decisions cannot be appealed, audited, or defended in regulator review, exposing the organisation to legal challenge and SDAIA non-compliance findings.',
       what_pass_looks_like = 'Per-model explainability documentation (model card, decision-rationale templates, or feature-importance reports) accessible to the affected subject and approved by the AI governance owner.'
 WHERE id = '101480b8-26d3-44b3-9dfa-b52284ca33ce'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Untested models embed protected-attribute bias that produces discriminatory outcomes at scale, breaching SDAIA fairness principles and exposing the organisation to discrimination claims.',
       what_pass_looks_like = 'A pre-deployment bias / fairness test report with defined protected attributes, measured disparity metrics, mitigation actions taken, and sign-off from the accountable authority.'
 WHERE id = '940f414b-7657-4acb-93b6-fcfc54bc26f2'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Without a named accountable authority, incidents, complaints, and model-drift findings have no owner and remediation timelines slip past SDAIA-required response windows.',
       what_pass_looks_like = 'A RACI matrix or accountability register naming the business owner, technical owner, and accountable authority with decision rights, dated before the system enters operation.'
 WHERE id = '955e2de6-ef00-4e40-a14d-2a7e44b4d104'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unclassified AI without human checkpoints lets critical decisions execute autonomously, removing the audit trail regulators and internal investigators need after harmful outcomes.',
       what_pass_looks_like = 'An SDAIA risk-tier classification, a human-in-the-loop policy for critical paths, and an immutable audit log of model outputs, human interventions, and final decisions.'
 WHERE id = '529a6289-f462-49e4-99c4-795dfe863b8e'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Procuring vendor AI without GRC evidence transfers regulatory risk to the buyer with no contractual leverage to demand explainability, bias data, or incident notifications post-signature.',
       what_pass_looks_like = 'RFP clauses citing SDAIA AI requirements plus vendor-supplied GRC artefacts (model card, bias report, security attestation, support SLA) attached to the signed contract.'
 WHERE id = '39c7650b-a19a-4945-96b0-473dd2c7fe9e'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unclassified or unvalidated training data leaks PDPL-regulated personal data into model weights and embeds quality defects that no post-hoc fix can fully remove.',
       what_pass_looks_like = 'Per-dataset classification per NDMO Data Classification Policy, a validation report covering quality and legality, and a training-use approval signed by the data owner.'
 WHERE id = '384e1eea-348e-426a-ae13-c3e81ce11741'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Models drift silently as inputs evolve; without monitored performance and drift metrics, accuracy decays into harmful errors before anyone notices the model is out of distribution.',
       what_pass_looks_like = 'A live monitoring dashboard tracking performance, drift, and impact metrics with thresholds linked to a documented retrain / rollback / retire workflow signed by the model owner.'
 WHERE id = 'de33b0dc-b524-46e7-9881-fbdf89ddf492'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Missing lifecycle documentation prevents reproducibility, makes decommissioning unauditable, and leaves orphaned models running long after the use case has ended.',
       what_pass_looks_like = 'An AI lifecycle dossier covering data sources, training runs, deployment configuration, monitoring metrics, and a decommissioning plan with retention rules per PDPL.'
 WHERE id = '02cb740c-8ba6-43e0-8785-7558ff233a3f'
   AND why_it_matters IS NULL;


-- ── Cyber security Compliance Check ──────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Unauthenticated or unverified devices become uncontrolled entry points; compromised endpoints persist on the network without the controls a Zero Trust posture provides.',
       what_pass_looks_like = 'A device authentication design citing certificate or MDM-based auth and continuous verification, aligned to NCA / NGCSRA Zero Trust expectations.'
 WHERE id = 'bdd778c9-496f-4a3a-a85f-ae049ae331cd'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Broad standing privileges magnify the blast radius of every credential compromise and breach NCA least-privilege requirements.',
       what_pass_looks_like = 'An IAM design with role-based access aligned to job function, periodic access review evidence, and a least-privilege policy enforcement mechanism.'
 WHERE id = '35d849f9-5781-4519-9069-5719cb686371'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Missing SSO / MFA enables credential-stuffing and phishing-driven account takeover, the dominant attack vector against government environments.',
       what_pass_looks_like = 'An IAM configuration showing SSO across all internal applications and MFA enforced for all internal users per NGCSRA policy with exceptions logged.'
 WHERE id = 'a77778a1-699d-4c1f-88fe-9e76395f2313'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Without monitoring, attacker dwell time runs into months; suspicious activity is only discovered after data has already been exfiltrated.',
       what_pass_looks_like = 'A SIEM ingestion design covering authentication, privilege escalation, and data-exfiltration events with alert rules tied to the incident response runbook.'
 WHERE id = 'c7fac74b-9e8e-41c8-a391-0134ba1129b9'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Flat networks without segmentation let an attacker escalate from a single foothold to crown jewels in one step.',
       what_pass_looks_like = 'A network design with zones / DMZ as applicable, firewall rule-set under change control, and IDS / IPS coverage for east-west and north-south traffic.'
 WHERE id = '7dae69d6-e694-4c7b-ace1-013c9aba8dd4'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Insecure third-party APIs become the supply-chain attack surface NCGR cannot directly patch but inherits the consequences of.',
       what_pass_looks_like = 'An API security design citing authentication (OAuth, mTLS), input validation, rate limiting, and the NGCSRA security control set the implementation conforms to.'
 WHERE id = '02c7a720-8bd3-43aa-8725-ef7666859902'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unassessed vendors introduce supply-chain risk that bypasses NCGR''s internal controls; without ongoing monitoring, vendor posture decays unnoticed.',
       what_pass_looks_like = 'A vendor risk-assessment record per integration with approval signature plus continuous monitoring evidence (SOC reports, posture scans) on a defined cadence.'
 WHERE id = 'bd45b61e-240a-4c27-8eb8-2ba39116c1ae'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Security retrofitted after build creates expensive rework and leaves design-level vulnerabilities (broken access control, missing encryption) that are hard to fully close.',
       what_pass_looks_like = 'A threat model and security architecture review showing authentication, authorisation, encryption, and secure-API patterns integrated at design stage, signed by security.'
 WHERE id = 'abeba7bc-c7c5-4218-848b-b70e8045405d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Implicit security requirements get cut under delivery pressure; if they are not written down with acceptance criteria, they do not get tested or accepted.',
       what_pass_looks_like = 'A non-functional requirements document listing security, compliance, and privacy requirements per NCA, NGCSRA, and PDPL with measurable acceptance criteria.'
 WHERE id = 'd9b630c2-c805-4c43-bd01-2445fb68ffff'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unpatched systems are the dominant exploit vector; NGCSRA defines timelines because every week of delay is statistically a week of additional exposure.',
       what_pass_looks_like = 'A patch management procedure citing NGCSRA timelines, plus a patch-status dashboard showing critical CVE compliance per asset class.'
 WHERE id = '153f5865-3dfb-4d6a-a55b-549f569af529'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Without rehearsed incident response, the first breach becomes an improvised crisis; containment slips past hours-to-detect into weeks-to-recover.',
       what_pass_looks_like = 'An incident response plan with breach playbooks, escalation matrix, communications templates, and a tested tabletop exercise within the last 12 months.'
 WHERE id = 'ca48147b-fe7a-4649-b6e8-c11d416ae49f'
   AND why_it_matters IS NULL;


-- ── Integration Compliance Check ─────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Bespoke integration mechanisms bypass NCGR''s monitoring, security, and lifecycle controls, creating opaque dependencies that fail unpredictably.',
       what_pass_looks_like = 'An integration design citing approved NCGR mechanisms (APIs, event-driven, messaging) with rationale for each choice referencing NCGR integration standards.'
 WHERE id = 'db0e41c8-dc57-4338-b06d-1323fc1b9ead'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Hard-coded integrations require code changes for trivial endpoint or mapping updates, slowing change and risking regression for routine operational tweaks.',
       what_pass_looks_like = 'An implementation showing integration flows in a configuration-driven tool (iPaaS, ESB, low-code) rather than custom scripts, with config under version control.'
 WHERE id = 'b34ebae4-781c-4063-9482-158c37e4e70a'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Off-tree integration choices break NCGR''s portfolio coherence and force one-off operational support patterns the integration team is not tooled for.',
       what_pass_looks_like = 'A decision-tree walkthrough showing the chosen approach matches NCGR''s documented integration decision criteria, with EA sign-off.'
 WHERE id = '540836a7-7b75-4b00-9cc4-e46edbfe6b99'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Silent integration failures corrupt downstream data for hours before anyone notices, turning a small fix into a multi-system reconciliation effort.',
       what_pass_looks_like = 'A monitoring design with per-interface success/failure metrics, latency thresholds, and on-call alerting routes documented in the operations runbook.'
 WHERE id = '23285e46-50ba-4de2-86e9-bafa33cb3076'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Untested integration points fail at production load or on the first malformed payload, with debugging done live during the outage.',
       what_pass_looks_like = 'A test-plan and report covering performance against target throughput, retry / DLQ behaviour, and error-handling paths, signed by QA before go-live.'
 WHERE id = '10e1f598-ac2f-4e5a-aa8e-f565714c9f3a'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Single-instance APIs become single points of failure for every dependent system, magnifying small incidents into platform-wide outages.',
       what_pass_looks_like = 'A deployment design showing APIs across multiple instances behind a load balancer with documented failover behaviour and capacity headroom.'
 WHERE id = '43d813f4-15a6-4735-8825-ba9a8953c9cb'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Middleware outages without failover halt every async workflow and queued message, with backlog recovery taking hours after service restoration.',
       what_pass_looks_like = 'An HA / DR design for middleware and brokers with tested automatic failover, plus a DR-site procedure with documented RTO.'
 WHERE id = '7b430eab-b651-420e-9c21-ae7814cbcc17'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Single-instance APIs are single points of failure that magnify incident impact across every dependent system (duplicate of Q6-S-INT-1.6).',
       what_pass_looks_like = 'Multi-instance API deployment behind a load balancer with documented failover and capacity headroom (duplicate of Q6-S-INT-1.6).'
 WHERE id = '9f904eac-a09a-4d18-8f87-d8e00182b7d8'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Off-platform integrations duplicate operational and licensing cost and produce a portfolio of unsupported one-offs the integration team cannot maintain.',
       what_pass_looks_like = 'A design document explicitly citing the NCGR integration platforms used and the standards (API spec, message schema) the implementation conforms to.'
 WHERE id = '26cbec69-ac18-4fd5-9adb-fd5811dbc66b'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Mismatched gateway use bypasses the security posture each gateway was selected for, exposing internal traffic externally or vice versa.',
       what_pass_looks_like = 'A traffic-flow diagram showing DataPower terminating internal traffic and APIGW terminating external traffic, with policies documented for each.'
 WHERE id = 'a5983bfb-82ad-42b7-9100-4b9bea2af452'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Bespoke file-transfer code lacks the audit, encryption, and reliability features IBM MFT provides, exposing file workflows to integrity and compliance gaps.',
       what_pass_looks_like = 'An integration design routing file transfers to FileNet or similar via IBM MFT with documented transfer policies and audit logging enabled.'
 WHERE id = '6963e7ef-2c83-4dbe-8807-74eed63f8cb0'
   AND why_it_matters IS NULL;


-- ── Application Compliance Check ─────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Building bespoke when a fit-for-purpose COTS or existing solution exists wastes budget and creates an additional maintenance burden NCGR must carry forever.',
       what_pass_looks_like = 'A build-vs-buy assessment listing candidate COTS / existing solutions evaluated, with the selection rationale signed off by the architecture board.'
 WHERE id = '3530e189-12cb-4a8b-827c-4d1fb7872816'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Single-unit solutions fragment NCGR''s application portfolio and miss cross-unit synergies that a slightly broader design would have captured cheaply.',
       what_pass_looks_like = 'A cross-unit applicability assessment naming other NCGR units that could adopt the solution and the modifications, if any, required to enable that.'
 WHERE id = '74d366f4-dff2-49eb-a3d2-8c1e4c4c576b'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Vendor lock-in turns routine renegotiation into hostage situations and forces costly rebuilds when the vendor changes terms or sunsets a product.',
       what_pass_looks_like = 'An architecture decision record citing portable interfaces, open standards, and a documented exit / migration path away from each proprietary component.'
 WHERE id = '2426e09e-3e77-4e7b-b671-2c36c0a14440'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Off-stack components fragment operational tooling, training, and licensing, raising support cost without delivering proportional benefit.',
       what_pass_looks_like = 'A stack-conformance matrix mapping every solution component to the NCGR approved technology stack, with deviations flagged and EA-approved.'
 WHERE id = '8c019200-8e61-4b6c-8f9c-2145d5ef7435'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'RFPs that omit modularity invite monolithic deliveries that cannot be incrementally changed without full-system regression cycles.',
       what_pass_looks_like = 'RFP clauses mandating modular design, component reuse, and maintainability targets with measurable acceptance criteria.'
 WHERE id = 'b347f70a-cb2d-440e-9fe3-7cd448b58cfa'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Tightly coupled modules force every fix to risk the whole application, slowing delivery and increasing the blast radius of every release.',
       what_pass_looks_like = 'A component diagram showing decoupled modules with documented interfaces, plus a change-impact analysis per module.'
 WHERE id = 'df7ffcf2-4f5e-40e9-beb4-0668a44f8780'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Manual deployments and manual operational tasks are the dominant source of preventable production incidents and consume scarce operations capacity.',
       what_pass_looks_like = 'An automation inventory listing CI/CD pipelines, scheduled-job orchestration, monitoring automation, and provisioning scripts in production use.'
 WHERE id = 'c87e7de3-df92-438e-9440-f8ffaf58a258'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Undocumented systems trap knowledge with the build team, leaving operations unable to support the system after handover.',
       what_pass_looks_like = 'An operations runbook covering deployment, monitoring, backup / restore, and incident response, plus signed-off knowledge-transfer sessions.'
 WHERE id = '4e371d49-72b6-4c80-9f4f-1c7b8408a861'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Tight coupling prevents incremental change; teams batch up risky big-bang releases instead of shipping small safe ones.',
       what_pass_looks_like = 'An interface design with explicit contracts (API specs, event schemas) per integration point, plus dependency analysis showing low coupling.'
 WHERE id = '748debbd-a6a2-4809-a517-e0a5f72a6186'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Without separated layers, business logic leaks into the UI and database, making it impossible to swap any layer without rewriting the others.',
       what_pass_looks_like = 'An architecture diagram showing separated presentation, business-logic, and data layers with documented dependencies running in one direction.'
 WHERE id = 'ea7b4466-d8e2-4bbe-b821-9cc488722286'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Excessive customisation of COTS turns a supported product into a bespoke fork, blocking vendor upgrades and inflating long-term cost.',
       what_pass_looks_like = 'A selection rationale plus a customisation register naming each modification, its impact on upgradability, and formal approval.'
 WHERE id = '153069ca-b4d1-49e5-938e-e5699de0cbca'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Non-scalable applications hit a ceiling that triggers a full redesign just as the business is succeeding and growth would have justified the investment.',
       what_pass_looks_like = 'A scaling design citing horizontal or vertical scale points, load-test evidence at projected peak, and the redesign triggers if any.'
 WHERE id = '5fc6fc1e-a554-489a-85f8-88972c756ff1'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Infrastructure sized only for today bottlenecks within the first growth cycle and forces emergency provisioning under business pressure.',
       what_pass_looks_like = 'A capacity model projecting compute, storage, and network needs over the next 3 years with documented scale-out / scale-up procedures.'
 WHERE id = 'fb738cdc-fa0b-4bde-b03e-57c029366771'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unoptimised workloads waste committed cloud spend or over-provisioned hardware, money that could fund the next initiative.',
       what_pass_looks_like = 'A cost-optimisation review citing right-sizing decisions, resource utilisation metrics, and a quarterly review cadence with the FinOps owner.'
 WHERE id = '9294fbe1-ac3a-40dc-b650-94f15f24b8f9'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Without HA and DR design, single failures take production offline for the duration of manual recovery, breaching SLA and continuity commitments.',
       what_pass_looks_like = 'An HA / DR design citing redundant components, failover triggers, and a tested DR runbook meeting the documented RTO and RPO.'
 WHERE id = 'da6bc1df-a291-4a37-a8cb-63c180a978fc'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'RFPs missing non-functional requirements get bids tuned only to functional spec, leaving NCGR to discover performance gaps in user acceptance testing.',
       what_pass_looks_like = 'RFP non-functional clauses naming target throughput, latency, and availability with measurable acceptance criteria and test method.'
 WHERE id = '58046539-4958-4b84-947b-6b6d4ca3d7e4'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Resilience and security bolted on late create single points of failure and exploitable gaps that are expensive to remediate post-build.',
       what_pass_looks_like = 'A design artefact (architecture review, threat model) showing resilience and security controls integrated at the design stage, signed by security and EA.'
 WHERE id = 'aa29e6db-72ab-4b7b-a5c7-994f35ca8ae5'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Missing or tamperable audit logs prevent incident reconstruction and breach NCGR''s compliance retention obligations after a security event.',
       what_pass_looks_like = 'A logging design citing log scope (critical actions / events), tamper-protection (write-once / signed), and retention period meeting NCGR / regulatory policy.'
 WHERE id = '2d44fc99-c1a8-4269-b34b-cde0b1fc721f'
   AND why_it_matters IS NULL;


-- ── Data Compliance Check ────────────────────────────────────────────

UPDATE public.framework_items
   SET why_it_matters       = 'Without conceptual / logical / physical models, data domains drift across systems, breaking integration and reporting consistency.',
       what_pass_looks_like = 'A versioned enterprise data model (conceptual, logical, physical) aligned to business domains and stored in the EA repository.'
 WHERE id = '9adacf71-9346-47ed-bed4-d878c3c20da3'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unowned data has no one to approve quality fixes, classification updates, or access requests, leaving issues to escalate unresolved.',
       what_pass_looks_like = 'A data governance charter naming domain owners, stewards, and custodians with a published RACI for data decisions.'
 WHERE id = 'b34eed02-c9c0-4e52-bc3a-f0a270f2a9bd'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unclassified data is treated identically regardless of sensitivity, exposing PDPL-regulated personal data to inappropriate access and storage.',
       what_pass_looks_like = 'Per-asset classification per the NDMO Data Classification Policy with enforcement controls (DLP, access policies) tied to each tier.'
 WHERE id = 'd4c525a3-e6ad-42c3-8e1f-777d2db6f6a3'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Indefinite retention breaches PDPL minimisation requirements; ad-hoc disposal leaves recoverable data on retired media.',
       what_pass_looks_like = 'A retention schedule per data class with archival and secure-disposal procedures, aligned to NCGR record-retention policy and PDPL.'
 WHERE id = 'a8d3ff70-48b6-4b8e-9ceb-51ba9da5f4ff'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Standing access to sensitive data violates least-privilege and creates large blast radius when an account is compromised.',
       what_pass_looks_like = 'An access-request workflow gating sensitive data behind ticketed approval, classification check, and time-bound grants logged in the IAM system.'
 WHERE id = '84d06ebf-49b6-4735-aba4-9b28fe577a7d'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Undetected quality decay corrupts downstream analytics and business decisions, with the cost of bad decisions far exceeding the cost of monitoring.',
       what_pass_looks_like = 'Automated quality checks for accuracy, completeness, and timeliness on key datasets, with results published to data stewards via a dashboard.'
 WHERE id = '4cd7f144-9f52-4c01-bc03-0c40669854fc'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Bespoke integrations bypass quality, security, and lineage controls, leaving data movement opaque to governance.',
       what_pass_looks_like = 'Integration design citing approved NCGR patterns (APIs, ETL/ELT, messaging) with quality checks and integrity validation at each hop.'
 WHERE id = '5f9f809d-dd01-441d-8d85-c532e6a0c236'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Without lineage, audit and impact-analysis questions cannot be answered without code archaeology, slowing change and audit response.',
       what_pass_looks_like = 'A lineage diagram per key dataset showing source systems, transformations, and consumers, maintained in the data-catalogue tool.'
 WHERE id = '765ef90c-18dd-42be-8443-44e8db1604ee'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unmanaged shadow analytics produce conflicting KPI numbers in different reports, eroding decision-maker trust in any data they see.',
       what_pass_looks_like = 'A KPI dictionary with formal definitions, approved source datasets / schemas per KPI, and a publication standard for BI reports.'
 WHERE id = 'fe8bbf25-192f-426f-af9e-5edbd8cbb5a2'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Unencrypted sensitive data breached at rest or intercepted in transit constitutes a PDPL incident with mandatory notification and remediation costs.',
       what_pass_looks_like = 'Encryption design citing approved cryptographic standards (e.g. AES-256, TLS 1.2+) covering all sensitive data stores and channels, with key-management documented.'
 WHERE id = '4acaf6cd-7fa2-41d6-98a6-80dde44847c2'
   AND why_it_matters IS NULL;

UPDATE public.framework_items
   SET why_it_matters       = 'Ungoverned encryption exceptions silently lower the security baseline; without approval and justification, the residual risk is invisible to security leadership.',
       what_pass_looks_like = 'An exception register entry per unencrypted asset citing technical justification, compensating controls, and time-boxed approval from the data owner.'
 WHERE id = '56e70b7f-ad52-4e82-ba68-90dc582ba425'
   AND why_it_matters IS NULL;


COMMIT;
