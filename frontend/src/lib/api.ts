/**
 * Typed API helpers for the FastAPI backend.
 *
 * The app is mounted at `/arch-assistant/` and the backend at
 * `/arch-assistant/api/`. In dev, Vite proxies the API path to
 * http://localhost:8000; in prod nginx does the same.
 */

const API_BASE = "/arch-assistant/api";

export const apiUrl = (path: string): string =>
  `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

/** URL of a stored image by its sha256 hash, suitable for an <img src>. */
export const imageUrl = (sha256: string): string =>
  apiUrl(`/images/${sha256}`);

// ── Types ──────────────────────────────────────────────────────────────

export type AnalysisMode =
  | "quick"
  | "detailed"
  | "persona"
  | "user_driven"
  | "compliance";
export type Persona = "data" | "network" | "security" | "enterprise";
export type SessionType = "analyze" | "compare";
export type SessionStatus = "running" | "done" | "error";

export interface HealthResponse {
  status: "ok" | "degraded" | "down";
  ollama_reachable: boolean;
  model_loaded: boolean;
  model_name: string;
  uptime_seconds: number;
  error: string | null;
}

export interface SessionListItem {
  id: string;
  session_type: SessionType;
  mode: string | null;
  persona: string | null;
  prompt_preview: string | null;
  status: SessionStatus;
  created_at: string;
  completed_at: string | null;
  total_ms: number | null;
}

export interface SessionDetail {
  id: string;
  session_type: SessionType;
  mode: string | null;
  persona: string | null;
  focus_areas: string[] | null;
  user_prompt: string | null;
  image_hash: string | null;
  reference_image_hash: string | null;
  response_markdown: string | null;
  scorecards: SavedScorecard[] | null;
  status: SessionStatus;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  ttft_ms: number | null;
  total_ms: number | null;
}

// ── Compliance scorecard (per-analysis result of compliance mode) ──────

/** One scored row of a compliance scorecard (per-analysis instance). */
export interface SavedScorecardItem {
  framework_item_id: string | null;
  criteria: string;
  weight_planned: number;
  /** 100 = Compliant, 50 = Partial, 0 = Not Compliant, null = Not Applicable. */
  compliance_pct: number | null;
  /** Citation produced by per-criterion mode. ADR id, section heading,
   *  table number, etc. Older sessions (single_pass) don't have this. */
  evidence?: string | null;
  remarks: string | null;
}

export interface SavedScorecard {
  framework_id: string;
  framework_name: string;
  narrative_markdown: string | null;
  weighted_score: number;
  items: SavedScorecardItem[];
}

export async function saveScorecards(
  sessionId: string,
  scorecards: SavedScorecard[],
): Promise<SessionDetail> {
  const r = await fetch(apiUrl(`/sessions/${sessionId}/scorecards`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scorecards }),
  });
  if (!r.ok)
    throw new Error(
      `PUT /sessions/${sessionId}/scorecards returned ${r.status}`,
    );
  return r.json();
}

// ── SSE event types ────────────────────────────────────────────────────

export type StreamEvent =
  | { type: "session_created"; id: string }
  | { type: "token"; content: string }
  | { type: "done"; ttft_ms?: number; total_ms?: number; eval_count?: number; prompt_eval_count?: number }
  | { type: "error"; code?: string; message?: string }
  | { type: "busy"; message?: string }
  // ── Compliance-mode events (single_pass + per_criterion share these) ──
  | {
      type: "framework_started";
      framework_id: string;
      framework_name: string;
      // single_pass uses item_count; per_criterion uses total_criteria. Both
      // optional so consumers can read whichever is present.
      item_count?: number;
      total_criteria?: number;
      items: Array<{
        idx: number;
        framework_item_id: string;
        /** Stable ID like "Q5-S-INF-1.3" — only emitted in per_criterion mode. */
        criterion_id?: string;
        criteria: string;
        weight_planned: number;
      }>;
    }
  | { type: "narrative_token"; framework_id: string; content: string }
  // ── single_pass-only event ──
  | {
      type: "scorecard_row";
      framework_id: string;
      idx: number;
      compliance_pct: number | null;
      remarks: string | null;
    }
  // ── per_criterion-only events ──
  | {
      type: "criterion_started";
      framework_id: string;
      idx: number;
      criterion_id: string;
    }
  | {
      type: "criterion_done";
      framework_id: string;
      idx: number;
      criterion_id: string;
      compliance_pct: number | null;
      evidence: string | null;
      remarks: string | null;
    }
  | {
      type: "framework_done";
      framework_id: string;
      weighted_score: number;
      /** Per-criterion mode includes the full saved scorecard payload. */
      scorecard?: SavedScorecard;
    };

/** Compliance scoring strategy. Plumbed to the backend as a form field. */
export type ScoringMode = "single_pass" | "per_criterion";

// ── Non-streaming endpoints ────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthResponse> {
  const r = await fetch(apiUrl("/health"));
  if (!r.ok) throw new Error(`/health returned ${r.status}`);
  return r.json();
}

export async function listSessions(
  limit = 50,
  offset = 0,
): Promise<SessionListItem[]> {
  const r = await fetch(apiUrl(`/sessions?limit=${limit}&offset=${offset}`));
  if (!r.ok) throw new Error(`/sessions returned ${r.status}`);
  return r.json();
}

export async function getSession(id: string): Promise<SessionDetail> {
  const r = await fetch(apiUrl(`/sessions/${id}`));
  if (!r.ok) throw new Error(`/sessions/${id} returned ${r.status}`);
  return r.json();
}

// ── Frameworks (EA compliance) ─────────────────────────────────────────

export interface FrameworkItem {
  id?: string;
  criteria: string;
  weight_planned: number;
  sort_order: number;
}

export interface FrameworkSummary {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  item_count: number;
}

export interface FrameworkDetail {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  items: FrameworkItem[];
}

export interface FrameworkUpsert {
  name: string;
  description: string | null;
  items: FrameworkItem[];
}

export async function listFrameworks(): Promise<FrameworkSummary[]> {
  const r = await fetch(apiUrl("/frameworks"));
  if (!r.ok) throw new Error(`/frameworks returned ${r.status}`);
  return r.json();
}

export async function getFramework(id: string): Promise<FrameworkDetail> {
  const r = await fetch(apiUrl(`/frameworks/${id}`));
  if (!r.ok) throw new Error(`/frameworks/${id} returned ${r.status}`);
  return r.json();
}

export async function createFramework(
  body: FrameworkUpsert,
): Promise<FrameworkDetail> {
  const r = await fetch(apiUrl("/frameworks"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`POST /frameworks returned ${r.status}`);
  return r.json();
}

export async function updateFramework(
  id: string,
  body: FrameworkUpsert,
): Promise<FrameworkDetail> {
  const r = await fetch(apiUrl(`/frameworks/${id}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`PUT /frameworks/${id} returned ${r.status}`);
  return r.json();
}

export async function deleteFramework(id: string): Promise<void> {
  const r = await fetch(apiUrl(`/frameworks/${id}`), { method: "DELETE" });
  if (!r.ok && r.status !== 204)
    throw new Error(`DELETE /frameworks/${id} returned ${r.status}`);
}

/** URL of the all-frameworks Excel export. Setting `window.location` to
 *  this triggers a normal browser download. */
export const frameworksExportUrl = (): string =>
  apiUrl("/frameworks/export.xlsx");

// ── Prompts (Settings → Prompts) ───────────────────────────────────────

export interface PromptItem {
  key: string;
  name: string;
  description: string;
  placeholders: string[];
  default_template: string;
  current_template: string;
  is_overridden: boolean;
  updated_at: string | null;
}

export async function listPrompts(): Promise<PromptItem[]> {
  const r = await fetch(apiUrl("/prompts"));
  if (!r.ok) throw new Error(`/prompts returned ${r.status}`);
  return r.json();
}

export async function savePromptOverride(
  key: string,
  template: string,
): Promise<PromptItem> {
  const r = await fetch(apiUrl(`/prompts/${key}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ template }),
  });
  if (!r.ok) {
    const detail = await r.text().catch(() => "");
    throw new Error(`PUT /prompts/${key} returned ${r.status}: ${detail.slice(0, 300)}`);
  }
  return r.json();
}

export async function resetPromptOverride(key: string): Promise<void> {
  const r = await fetch(apiUrl(`/prompts/${key}`), { method: "DELETE" });
  if (!r.ok && r.status !== 204)
    throw new Error(`DELETE /prompts/${key} returned ${r.status}`);
}

export interface PromptOverrideStatus {
  key: string;
  has_override: boolean;
  /** Current default's version, or null if this prompt isn't version-tracked. */
  default_version: string | null;
}

export async function getPromptOverrideStatus(
  key: string,
): Promise<PromptOverrideStatus> {
  const r = await fetch(apiUrl(`/prompts/${key}/override-status`));
  if (!r.ok) throw new Error(`GET /prompts/${key}/override-status returned ${r.status}`);
  return r.json();
}
