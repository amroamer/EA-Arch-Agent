/**
 * Renders the live + editable compliance scorecards produced by Analyze
 * mode=compliance. Consumes the SSE event stream from useStreamingFetch and
 * derives one card per framework, each with:
 *   - per-framework narrative (markdown, fills as narrative_token arrives)
 *   - scorecard table (rows fill as scorecard_row events arrive)
 *   - editable compliance dropdown + remarks once the framework finishes
 *   - one Save button at the bottom that PUTs all scorecards to the session
 *
 * Read-only fallback (mode === "view"): pass `initial` instead of `events`
 * to render saved scorecards from a History detail view.
 */
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Loader2,
  AlertCircle,
  CheckCircle2,
  Save,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  saveScorecards,
  type SavedScorecard,
  type SavedScorecardItem,
  type StreamEvent,
} from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────

interface RowState {
  framework_item_id: string;
  criteria: string;
  weight_planned: number;
  /** 100 / 50 / 0 / null. Undefined while still streaming. */
  compliance_pct: number | null | undefined;
  remarks: string | null | undefined;
}

interface FrameworkState {
  id: string;
  name: string;
  narrative: string;
  isDone: boolean;
  weightedScore: number | null;
  rows: RowState[];
}

interface Props {
  status: "idle" | "streaming" | "done" | "error" | "busy";
  error?: string;
  sessionId?: string;
  events: StreamEvent[];
  ttftMs?: number;
  totalMs?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────

const COMPLIANCE_OPTIONS: { value: string; label: string; pct: number | null }[] = [
  { value: "100", label: "Compliant", pct: 100 },
  { value: "50", label: "Partially Compliant", pct: 50 },
  { value: "0", label: "Not Compliant", pct: 0 },
  { value: "na", label: "Not Applicable", pct: null },
];

function pctToValue(pct: number | null | undefined): string {
  if (pct === null || pct === undefined) return "na";
  if (pct >= 75) return "100";
  if (pct >= 25) return "50";
  return "0";
}

function valueToPct(v: string): number | null {
  const opt = COMPLIANCE_OPTIONS.find((o) => o.value === v);
  return opt ? opt.pct : null;
}

function complianceTone(pct: number | null | undefined): {
  bg: string;
  text: string;
  label: string;
} {
  if (pct === null || pct === undefined)
    return { bg: "bg-gray-200", text: "text-gray-600", label: "N/A" };
  if (pct >= 75)
    return { bg: "bg-status-green", text: "text-white", label: "Compliant" };
  if (pct >= 25)
    return {
      bg: "bg-status-yellow",
      text: "text-kpmg-darkBlue",
      label: "Partial",
    };
  return { bg: "bg-status-red", text: "text-white", label: "Not Compliant" };
}

function computeWeightedScore(rows: RowState[]): number {
  let num = 0;
  let denom = 0;
  for (const r of rows) {
    if (r.compliance_pct === null || r.compliance_pct === undefined) continue;
    const w = Number(r.weight_planned) || 0;
    num += w * Number(r.compliance_pct);
    denom += w;
  }
  return denom > 0 ? num / denom : 0;
}

/** Build the per-framework state from the cumulative event stream. */
function deriveFromEvents(events: StreamEvent[]): FrameworkState[] {
  const map = new Map<string, FrameworkState>();
  const order: string[] = [];
  for (const evt of events) {
    if (evt.type === "framework_started") {
      if (!map.has(evt.framework_id)) {
        order.push(evt.framework_id);
        map.set(evt.framework_id, {
          id: evt.framework_id,
          name: evt.framework_name,
          narrative: "",
          isDone: false,
          weightedScore: null,
          rows: evt.items.map((it) => ({
            framework_item_id: it.framework_item_id,
            criteria: it.criteria,
            weight_planned: it.weight_planned,
            compliance_pct: undefined,
            remarks: undefined,
          })),
        });
      }
    } else if (evt.type === "narrative_token") {
      const fw = map.get(evt.framework_id);
      if (fw) fw.narrative += evt.content;
    } else if (evt.type === "scorecard_row") {
      const fw = map.get(evt.framework_id);
      if (fw && evt.idx >= 0 && evt.idx < fw.rows.length) {
        fw.rows[evt.idx] = {
          ...fw.rows[evt.idx],
          compliance_pct: evt.compliance_pct,
          remarks: evt.remarks,
        };
      }
    } else if (evt.type === "framework_done") {
      const fw = map.get(evt.framework_id);
      if (fw) {
        fw.isDone = true;
        fw.weightedScore = evt.weighted_score;
      }
    }
  }
  return order.map((id) => map.get(id)!);
}

// ── Component ─────────────────────────────────────────────────────────────

export function ComplianceScorecards({
  status,
  error,
  sessionId,
  events,
  ttftMs,
  totalMs,
}: Props) {
  // Streaming-derived state.
  const streamed = useMemo(() => deriveFromEvents(events), [events]);

  // Local editable state — keyed by framework_id. Once a framework is `isDone`
  // we copy its streamed rows here so user edits aren't overwritten by
  // subsequent renders (stream events keep arriving for other frameworks).
  const [editable, setEditable] = useState<Record<string, RowState[]>>({});
  // Track which frameworks we've already copied to avoid clobbering edits.
  const [copied, setCopied] = useState<Set<string>>(new Set());

  useEffect(() => {
    let dirty = false;
    const nextEditable: Record<string, RowState[]> = { ...editable };
    const nextCopied = new Set(copied);
    for (const fw of streamed) {
      if (fw.isDone && !copied.has(fw.id)) {
        nextEditable[fw.id] = fw.rows.map((r) => ({ ...r }));
        nextCopied.add(fw.id);
        dirty = true;
      }
    }
    if (dirty) {
      setEditable(nextEditable);
      setCopied(nextCopied);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [streamed]);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const updateRow = (fwId: string, idx: number, patch: Partial<RowState>) => {
    setSavedAt(null);
    setEditable((prev) => {
      const rows = (prev[fwId] || []).map((r, i) =>
        i === idx ? { ...r, ...patch } : r,
      );
      return { ...prev, [fwId]: rows };
    });
  };

  const onSave = async () => {
    if (!sessionId) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload: SavedScorecard[] = streamed.map((fw) => {
        const rows = editable[fw.id] || fw.rows;
        const items: SavedScorecardItem[] = rows.map((r) => ({
          framework_item_id: r.framework_item_id,
          criteria: r.criteria,
          weight_planned: r.weight_planned,
          compliance_pct:
            r.compliance_pct === undefined ? null : r.compliance_pct,
          remarks: r.remarks ?? null,
        }));
        return {
          framework_id: fw.id,
          framework_name: fw.name,
          narrative_markdown: fw.narrative || null,
          weighted_score: computeWeightedScore(rows),
          items,
        };
      });
      await saveScorecards(sessionId, payload);
      setSavedAt(Date.now());
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const allDone =
    streamed.length > 0 && streamed.every((fw) => fw.isDone) && status === "done";

  return (
    <section className="space-y-4" aria-busy={status === "streaming"}>
      {/* Status bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm">
        <div className="flex items-center gap-2">
          {status === "streaming" && (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-kpmg-blue" />
              <span className="text-kpmg-blue">
                Scoring {streamed.length || "…"}{" "}
                framework{streamed.length === 1 ? "" : "s"}…
              </span>
            </>
          )}
          {status === "done" && (
            <>
              <CheckCircle2 className="h-4 w-4 text-status-green" />
              <span className="text-status-green">Done</span>
              {totalMs !== undefined && (
                <span className="text-gray-500">
                  • {(totalMs / 1000).toFixed(1)} s
                  {ttftMs ? ` (TTFT ${(ttftMs / 1000).toFixed(2)} s)` : ""}
                </span>
              )}
            </>
          )}
          {status === "busy" && (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-status-yellow" />
              <span className="text-status-yellow">
                Model in use — your request is queued
              </span>
            </>
          )}
          {status === "error" && (
            <>
              <AlertCircle className="h-4 w-4 text-status-red" />
              <span className="text-status-red">Error</span>
              {error && <span className="text-gray-500">— {error}</span>}
            </>
          )}
        </div>
        {allDone && sessionId && (
          <div className="flex items-center gap-3">
            {savedAt && !saveError && (
              <span className="inline-flex items-center gap-1 text-xs text-status-green">
                <CheckCircle2 className="h-3 w-3" />
                Saved
              </span>
            )}
            {saveError && (
              <span className="inline-flex items-center gap-1 text-xs text-status-red">
                <AlertCircle className="h-3 w-3" />
                {saveError}
              </span>
            )}
            <Button onClick={onSave} disabled={saving} size="sm">
              {saving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save scorecards
            </Button>
          </div>
        )}
      </div>

      {/* Per-framework cards */}
      {streamed.length === 0 && status === "streaming" && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-2">
              <div className="h-3 w-2/3 animate-pulse rounded bg-gray-100" />
              <div className="h-3 w-5/6 animate-pulse rounded bg-gray-100" />
              <div className="h-3 w-1/2 animate-pulse rounded bg-gray-100" />
            </div>
          </CardContent>
        </Card>
      )}

      {streamed.map((fw) => {
        // For done frameworks, render from editable state; for streaming, from
        // the freshly derived state.
        const rows = fw.isDone && editable[fw.id] ? editable[fw.id] : fw.rows;
        const liveScore = fw.isDone ? computeWeightedScore(rows) : fw.weightedScore;
        return (
          <FrameworkCard
            key={fw.id}
            fw={fw}
            rows={rows}
            score={liveScore}
            editable={fw.isDone}
            onUpdateRow={(idx, patch) => updateRow(fw.id, idx, patch)}
          />
        );
      })}
    </section>
  );
}

// ── One framework card ────────────────────────────────────────────────────

interface CardProps {
  fw: FrameworkState;
  rows: RowState[];
  score: number | null;
  editable: boolean;
  onUpdateRow: (idx: number, patch: Partial<RowState>) => void;
}

function FrameworkCard({ fw, rows, score, editable, onUpdateRow }: CardProps) {
  return (
    <Card>
      <CardContent className="p-6">
        {/* Header */}
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-kpmg-darkBlue">
              {fw.name}
            </h3>
            <p className="text-xs text-gray-500">
              {rows.length} criteria
              {fw.isDone ? " · scored" : " · scoring…"}
            </p>
          </div>
          <ScorePill score={score} streaming={!fw.isDone} />
        </div>

        {/* Narrative */}
        {fw.narrative ? (
          <article className="md-content mb-4 rounded-md border border-gray-100 bg-gray-50/50 p-4">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {fw.narrative}
            </ReactMarkdown>
          </article>
        ) : !fw.isDone ? (
          <div className="mb-4 space-y-2">
            <div className="h-3 w-2/3 animate-pulse rounded bg-gray-100" />
            <div className="h-3 w-5/6 animate-pulse rounded bg-gray-100" />
          </div>
        ) : null}

        {/* Scorecard table */}
        <div className="overflow-hidden rounded-lg border border-gray-200">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500">
              <tr>
                <th className="w-10 px-3 py-2 text-center font-medium">#</th>
                <th className="px-3 py-2 font-medium">Criteria</th>
                <th className="w-20 px-3 py-2 text-right font-medium">
                  Weight
                </th>
                <th className="w-44 px-3 py-2 font-medium">Compliance</th>
                <th className="px-3 py-2 font-medium">Remarks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {rows.map((r, idx) => {
                const tone = complianceTone(r.compliance_pct);
                const value = pctToValue(r.compliance_pct);
                return (
                  <tr key={idx} className="align-top">
                    <td className="p-3 pt-3.5 text-center">
                      <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-kpmg-blue/10 text-xs font-semibold text-kpmg-blue tabular-nums">
                        {idx + 1}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-sm leading-snug text-kpmg-darkBlue">
                      {r.criteria}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-sm tabular-nums">
                      {r.weight_planned.toFixed(1)}
                    </td>
                    <td className="px-3 py-2">
                      {editable ? (
                        <select
                          value={value}
                          onChange={(e) =>
                            onUpdateRow(idx, {
                              compliance_pct: valueToPct(e.target.value),
                            })
                          }
                          className={cn(
                            "w-full rounded border border-gray-200 bg-white px-2 py-1.5 text-sm focus:border-kpmg-blue focus:outline-none",
                          )}
                        >
                          {COMPLIANCE_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      ) : r.compliance_pct === undefined ? (
                        <span className="inline-flex items-center gap-1 text-xs text-gray-400">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          waiting…
                        </span>
                      ) : (
                        <span
                          className={cn(
                            "inline-block rounded px-2 py-0.5 text-xs font-medium",
                            tone.bg,
                            tone.text,
                          )}
                        >
                          {tone.label}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      {editable ? (
                        <Textarea
                          value={r.remarks ?? ""}
                          onChange={(e) =>
                            onUpdateRow(idx, {
                              remarks: e.target.value || null,
                            })
                          }
                          className="min-h-[40px] resize-y text-sm"
                          placeholder="Notes…"
                        />
                      ) : (
                        <span className="text-sm text-gray-700">
                          {r.remarks ?? (
                            <span className="text-gray-300">—</span>
                          )}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function ScorePill({
  score,
  streaming,
}: {
  score: number | null;
  streaming: boolean;
}) {
  if (score === null) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-500">
        <Loader2
          className={cn("h-3 w-3", streaming && "animate-spin")}
        />
        Pending
      </span>
    );
  }
  const tone =
    score >= 80
      ? { bg: "bg-status-green/15", text: "text-status-green", dot: "bg-status-green" }
      : score >= 50
        ? { bg: "bg-status-yellow/20", text: "text-kpmg-darkBlue", dot: "bg-status-yellow" }
        : { bg: "bg-status-red/15", text: "text-status-red", dot: "bg-status-red" };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold",
        tone.bg,
        tone.text,
      )}
    >
      <Target className="h-3.5 w-3.5" />
      <span className="tabular-nums">{score.toFixed(1)}%</span>
      <span className={cn("h-1.5 w-1.5 rounded-full", tone.dot)} />
    </span>
  );
}

// ── Read-only renderer for History/SessionDetail ──────────────────────────

export function SavedScorecardsView({
  scorecards,
}: {
  scorecards: SavedScorecard[];
}) {
  return (
    <section className="space-y-4">
      {scorecards.map((sc) => {
        const fwState: FrameworkState = {
          id: sc.framework_id,
          name: sc.framework_name,
          narrative: sc.narrative_markdown ?? "",
          isDone: true,
          weightedScore: sc.weighted_score,
          rows: sc.items.map((it) => ({
            framework_item_id: it.framework_item_id ?? "",
            criteria: it.criteria,
            weight_planned: it.weight_planned,
            compliance_pct: it.compliance_pct,
            remarks: it.remarks,
          })),
        };
        return (
          <FrameworkCard
            key={sc.framework_id}
            fw={fwState}
            rows={fwState.rows}
            score={sc.weighted_score}
            editable={false}
            onUpdateRow={() => {}}
          />
        );
      })}
    </section>
  );
}
