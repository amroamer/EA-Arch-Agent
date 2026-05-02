/**
 * Settings → EA Compliance Framework editor.
 *
 *  Left column: list of frameworks + "+ New" button.
 *  Right column: editor for the selected framework — name, description,
 *                a total-weight headline card, and a table of criteria with
 *                their planned weights. weight_actual / compliance_pct /
 *                remarks live with the per-analysis flow, not the framework
 *                template, so they are not exposed here. Save replaces
 *                everything atomically.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Plus,
  Trash2,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ListChecks,
  Target,
  Download,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  createFramework,
  deleteFramework,
  frameworksExportUrl,
  getFramework,
  listFrameworks,
  updateFramework,
  type FrameworkDetail,
  type FrameworkItem,
  type FrameworkSummary,
} from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────────

function emptyItem(sort_order: number): FrameworkItem {
  return {
    criteria: "",
    weight_planned: 0,
    sort_order,
    why_it_matters: null,
    what_pass_looks_like: null,
  };
}

function hasRationale(it: FrameworkItem): boolean {
  return Boolean(
    (it.why_it_matters && it.why_it_matters.trim()) ||
      (it.what_pass_looks_like && it.what_pass_looks_like.trim()),
  );
}

/** Tone for the total-weight headline relative to the 100% target. */
function weightTone(total: number): {
  badgeBg: string;
  badgeText: string;
  label: string;
  bar: string;
} {
  const delta = Math.abs(total - 100);
  if (delta < 0.5)
    return {
      badgeBg: "bg-status-green/15",
      badgeText: "text-status-green",
      label: "Balanced",
      bar: "bg-status-green",
    };
  if (delta <= 5)
    return {
      badgeBg: "bg-status-yellow/20",
      badgeText: "text-kpmg-darkBlue",
      label: total > 100 ? "Slightly over" : "Slightly under",
      bar: "bg-status-yellow",
    };
  return {
    badgeBg: "bg-status-red/15",
    badgeText: "text-status-red",
    label: total > 100 ? "Over allocated" : "Under allocated",
    bar: "bg-status-red",
  };
}

// Drop fields the API doesn't expect / will regenerate.
function stripForSave(items: FrameworkItem[]): FrameworkItem[] {
  return items.map(({ id: _id, ...rest }, idx) => ({
    ...rest,
    sort_order: idx,
  }));
}

// ── Page ───────────────────────────────────────────────────────────────

export default function FrameworkSettings() {
  const [list, setList] = useState<FrameworkSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<FrameworkDetail | null>(null);
  const [originalJson, setOriginalJson] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  // Indices of rows whose rationale block is expanded. Collapsed by default
  // even when fields are populated — the indicator pill makes presence visible.
  const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

  const toggleExpanded = (idx: number) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const refreshList = useCallback(async () => {
    try {
      const rows = await listFrameworks();
      setList(rows);
      return rows;
    } catch (e) {
      setError((e as Error).message);
      return [];
    }
  }, []);

  // Initial load
  useEffect(() => {
    refreshList();
  }, [refreshList]);

  // Load detail when selection changes
  useEffect(() => {
    let cancelled = false;
    if (!selectedId) {
      setDraft(null);
      setOriginalJson("");
      return;
    }
    (async () => {
      setLoading(true);
      try {
        const d = await getFramework(selectedId);
        if (!cancelled) {
          setDraft(d);
          setOriginalJson(JSON.stringify(d));
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const dirty = useMemo(
    () => !!draft && JSON.stringify(draft) !== originalJson,
    [draft, originalJson],
  );

  // ── Derived totals ───────────────────────────────────────────────────
  const totals = useMemo(() => {
    if (!draft) return { planned: 0 };
    let planned = 0;
    for (const it of draft.items) {
      planned += Number(it.weight_planned) || 0;
    }
    return { planned };
  }, [draft]);

  // ── Handlers ─────────────────────────────────────────────────────────

  const handleNew = async () => {
    setError(null);
    try {
      const created = await createFramework({
        name: "New Framework",
        description: null,
        items: [],
      });
      const rows = await refreshList();
      setSelectedId(created.id);
      void rows;
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const handleSave = async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateFramework(draft.id, {
        name: draft.name,
        description: draft.description,
        items: stripForSave(draft.items),
      });
      setDraft(updated);
      setOriginalJson(JSON.stringify(updated));
      setSavedAt(Date.now());
      await refreshList();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!draft) return;
    if (!confirm(`Delete framework "${draft.name}"? This cannot be undone.`))
      return;
    try {
      await deleteFramework(draft.id);
      setSelectedId(null);
      setDraft(null);
      await refreshList();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const updateDraft = (patch: Partial<FrameworkDetail>) => {
    setDraft((d) => (d ? { ...d, ...patch } : d));
  };

  const updateItem = (idx: number, patch: Partial<FrameworkItem>) => {
    setDraft((d) =>
      d
        ? {
            ...d,
            items: d.items.map((it, i) => (i === idx ? { ...it, ...patch } : it)),
          }
        : d,
    );
  };

  const addItem = () => {
    setDraft((d) =>
      d ? { ...d, items: [...d.items, emptyItem(d.items.length)] } : d,
    );
  };

  const removeItem = (idx: number) => {
    setDraft((d) =>
      d ? { ...d, items: d.items.filter((_, i) => i !== idx) } : d,
    );
  };

  // ── Render ───────────────────────────────────────────────────────────

  const exportDisabled = !list || list.length === 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-kpmg-darkBlue">
            EA Compliance Framework
          </h1>
          <p className="text-gray-600">
            Define reusable compliance scorecards — frameworks like AWS
            Well-Architected, TOGAF, or Zero Trust. Each framework holds a list
            of criteria with planned vs actual weights and a compliance score.
          </p>
        </div>
        <Button
          asChild={!exportDisabled}
          variant="outline"
          disabled={exportDisabled}
          title={
            exportDisabled
              ? "No frameworks to export"
              : "Download all frameworks as a single .xlsx workbook"
          }
        >
          {exportDisabled ? (
            <span>
              <Download className="h-4 w-4" />
              Export to Excel
            </span>
          ) : (
            <a href={frameworksExportUrl()} download>
              <Download className="h-4 w-4" />
              Export to Excel
            </a>
          )}
        </Button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-status-red/40 bg-status-red/5 p-3 text-sm text-status-red">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="ml-auto text-xs underline"
          >
            dismiss
          </button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        {/* ── Left: list of frameworks ────────────────────────────────── */}
        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
            <CardTitle className="text-base">Frameworks</CardTitle>
            <Button size="sm" onClick={handleNew}>
              <Plus className="h-4 w-4" />
              New
            </Button>
          </CardHeader>
          <CardContent className="p-2 pt-0">
            {list === null ? (
              <div className="space-y-2 p-2">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : list.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-gray-500">
                No frameworks yet. Click "New" to create one.
              </p>
            ) : (
              <ul className="space-y-1">
                {list.map((fw) => {
                  const active = fw.id === selectedId;
                  return (
                    <li key={fw.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(fw.id)}
                        className={cn(
                          "flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm",
                          "transition-colors",
                          active
                            ? "bg-kpmg-blue text-white"
                            : "hover:bg-kpmg-lightBlue/40 text-kpmg-darkBlue",
                        )}
                      >
                        <span className="flex-1 truncate font-medium">
                          {fw.name}
                        </span>
                        <span
                          className={cn(
                            "shrink-0 rounded px-1.5 py-0.5 text-[11px]",
                            active
                              ? "bg-white/20"
                              : "bg-gray-100 text-gray-600",
                          )}
                        >
                          {fw.item_count}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* ── Right: editor ───────────────────────────────────────────── */}
        <Card>
          <CardContent className="p-6">
            {!selectedId ? (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <ListChecks className="h-10 w-10 text-gray-300" />
                <p className="text-gray-500">
                  Select a framework on the left, or click <strong>New</strong>{" "}
                  to create one.
                </p>
              </div>
            ) : loading || !draft ? (
              <div className="space-y-3">
                <Skeleton className="h-10 w-1/3" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-40 w-full" />
              </div>
            ) : (
              <div className="space-y-5">
                {/* Header: name + actions */}
                <div className="flex items-start gap-3">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="fw-name">Name</Label>
                    <Input
                      id="fw-name"
                      value={draft.name}
                      onChange={(e) => updateDraft({ name: e.target.value })}
                    />
                  </div>
                  <div className="flex flex-col gap-2 pt-7">
                    <Button
                      onClick={handleSave}
                      disabled={!dirty || saving}
                      title={dirty ? "Save changes" : "No unsaved changes"}
                    >
                      {saving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      Save
                    </Button>
                    <Button
                      variant="outline"
                      onClick={handleDelete}
                      className="border-status-red text-status-red hover:bg-status-red/10"
                    >
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="fw-desc">Description</Label>
                  <Textarea
                    id="fw-desc"
                    value={draft.description ?? ""}
                    onChange={(e) =>
                      updateDraft({ description: e.target.value || null })
                    }
                    placeholder="Optional — what does this framework measure?"
                    className="min-h-[60px]"
                  />
                </div>

                {/* Saved/dirty pill */}
                <div className="flex items-center gap-2 text-xs">
                  {dirty ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-status-yellow/20 px-2.5 py-1 font-medium text-kpmg-darkBlue">
                      <span className="h-1.5 w-1.5 rounded-full bg-status-yellow" />
                      Unsaved changes
                    </span>
                  ) : savedAt ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-status-green/15 px-2.5 py-1 font-medium text-status-green">
                      <CheckCircle2 className="h-3 w-3" />
                      Saved
                    </span>
                  ) : null}
                </div>

                {/* Total-weight headline card */}
                {(() => {
                  const tone = weightTone(totals.planned);
                  const pctOfBar = Math.min(
                    100,
                    Math.max(0, (totals.planned / 100) * 100),
                  );
                  return (
                    <div className="rounded-xl border border-kpmg-blue/15 bg-gradient-to-br from-kpmg-blue/5 via-white to-kpmg-pacificBlue/5 p-5 shadow-sm">
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-gray-500">
                            <Target className="h-3.5 w-3.5" />
                            Total weight
                          </div>
                          <div className="mt-1.5 flex items-baseline gap-2">
                            <span className="text-5xl font-bold tabular-nums text-kpmg-darkBlue">
                              {totals.planned.toFixed(1)}
                            </span>
                            <span className="text-2xl font-medium tabular-nums text-gray-400">
                              / 100
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-1.5">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold",
                              tone.badgeBg,
                              tone.badgeText,
                            )}
                          >
                            <span
                              className={cn("h-1.5 w-1.5 rounded-full", tone.bar)}
                            />
                            {tone.label}
                          </span>
                          <p className="text-xs text-gray-500">
                            {draft.items.length}{" "}
                            {draft.items.length === 1 ? "criterion" : "criteria"}
                            {Math.abs(totals.planned - 100) >= 0.5 && (
                              <>
                                {" · "}
                                <span className="font-medium text-kpmg-darkBlue">
                                  {totals.planned > 100 ? "+" : ""}
                                  {(totals.planned - 100).toFixed(1)} from target
                                </span>
                              </>
                            )}
                          </p>
                        </div>
                      </div>
                      <div className="mt-4 h-2 overflow-hidden rounded-full bg-gray-200/70">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all duration-500",
                            tone.bar,
                          )}
                          style={{ width: `${pctOfBar}%` }}
                        />
                      </div>
                    </div>
                  );
                })()}

                {/* Items table */}
                <div className="overflow-hidden rounded-lg border border-gray-200">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-left text-xs uppercase tracking-wider text-gray-500">
                      <tr>
                        <th className="w-12 px-3 py-3 text-center font-medium">
                          #
                        </th>
                        <th className="px-3 py-3 font-medium">Criteria</th>
                        <th className="w-32 px-3 py-3 text-right font-medium">
                          Weight (%)
                        </th>
                        <th className="w-12 px-3 py-3" aria-label="Delete" />
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 bg-white">
                      {draft.items.length === 0 && (
                        <tr>
                          <td
                            colSpan={4}
                            className="px-3 py-12 text-center text-sm text-gray-400"
                          >
                            <ListChecks className="mx-auto mb-2 h-8 w-8 text-gray-300" />
                            No criteria yet. Click <strong>Add criterion</strong> below.
                          </td>
                        </tr>
                      )}
                      {draft.items.map((it, idx) => (
                        <tr
                          key={idx}
                          className="align-top transition-colors hover:bg-gray-50/60"
                        >
                          <td className="p-3 pt-4 text-center">
                            <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-kpmg-blue/10 text-xs font-semibold text-kpmg-blue tabular-nums">
                              {idx + 1}
                            </span>
                          </td>
                          <td className="p-2">
                            <Textarea
                              value={it.criteria}
                              onChange={(e) =>
                                updateItem(idx, { criteria: e.target.value })
                              }
                              placeholder="e.g., All public-facing endpoints terminate TLS at the ALB"
                              className="min-h-[56px] resize-y text-sm leading-relaxed"
                            />
                            <button
                              type="button"
                              onClick={() => toggleExpanded(idx)}
                              className="mt-1.5 inline-flex items-center gap-1 text-xs text-gray-500 hover:text-kpmg-blue"
                              aria-expanded={expandedRows.has(idx)}
                              aria-controls={`rationale-${idx}`}
                            >
                              {expandedRows.has(idx) ? (
                                <ChevronDown className="h-3.5 w-3.5" />
                              ) : (
                                <ChevronRight className="h-3.5 w-3.5" />
                              )}
                              {hasRationale(it) ? "Edit rationale" : "Add rationale"}
                              {hasRationale(it) && !expandedRows.has(idx) && (
                                <span
                                  className="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-status-green"
                                  aria-label="Rationale set"
                                  title="Rationale set"
                                />
                              )}
                            </button>
                            {expandedRows.has(idx) && (
                              <div
                                id={`rationale-${idx}`}
                                className="mt-2 space-y-2 rounded-md border border-gray-200 bg-gray-50/60 p-2"
                              >
                                <div className="space-y-1">
                                  <Label
                                    htmlFor={`why-${idx}`}
                                    className="text-xs font-medium text-gray-600"
                                  >
                                    Why this matters
                                  </Label>
                                  <Textarea
                                    id={`why-${idx}`}
                                    value={it.why_it_matters ?? ""}
                                    onChange={(e) =>
                                      updateItem(idx, {
                                        why_it_matters: e.target.value || null,
                                      })
                                    }
                                    placeholder="One sentence on the risk this criterion protects against."
                                    maxLength={200}
                                    className="min-h-[44px] resize-y text-sm leading-relaxed"
                                  />
                                </div>
                                <div className="space-y-1">
                                  <Label
                                    htmlFor={`pass-${idx}`}
                                    className="text-xs font-medium text-gray-600"
                                  >
                                    What a pass looks like
                                  </Label>
                                  <Textarea
                                    id={`pass-${idx}`}
                                    value={it.what_pass_looks_like ?? ""}
                                    onChange={(e) =>
                                      updateItem(idx, {
                                        what_pass_looks_like: e.target.value || null,
                                      })
                                    }
                                    placeholder="One sentence on the concrete evidence that constitutes a pass."
                                    maxLength={200}
                                    className="min-h-[44px] resize-y text-sm leading-relaxed"
                                  />
                                </div>
                              </div>
                            )}
                          </td>
                          <td className="p-2">
                            <Input
                              type="number"
                              min={0}
                              max={100}
                              step={0.5}
                              value={it.weight_planned}
                              onChange={(e) =>
                                updateItem(idx, {
                                  weight_planned: Number(e.target.value) || 0,
                                })
                              }
                              className="text-right tabular-nums"
                            />
                          </td>
                          <td className="p-2 pt-3">
                            <Button
                              type="button"
                              size="icon"
                              variant="ghost"
                              onClick={() => removeItem(idx)}
                              aria-label={`Remove row ${idx + 1}`}
                              className="text-gray-300 hover:bg-status-red/10 hover:text-status-red"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    {draft.items.length > 0 && (
                      <tfoot className="bg-gray-50 text-xs">
                        <tr>
                          <td colSpan={2} className="px-3 py-2.5 text-right font-medium uppercase tracking-wider text-gray-500">
                            Total
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono text-sm font-semibold text-kpmg-darkBlue tabular-nums">
                            {totals.planned.toFixed(1)}
                          </td>
                          <td />
                        </tr>
                      </tfoot>
                    )}
                  </table>
                </div>

                <Button
                  variant="outline"
                  onClick={addItem}
                  className="w-full border-dashed text-gray-600 hover:border-kpmg-blue hover:bg-kpmg-blue/5 hover:text-kpmg-blue"
                >
                  <Plus className="h-4 w-4" />
                  Add criterion
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
