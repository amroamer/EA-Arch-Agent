/**
 * Settings → Prompts editor.
 *
 *  Left column : list of all built-in prompts (with an "Overridden" pill
 *                next to keys the user has customised).
 *  Right column: editor — name, description, available {placeholders},
 *                large textarea, Save + Reset-to-default buttons.
 *
 * Saving validates server-side that all required placeholders still
 * appear in the template; a 400 surfaces inline.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Sparkles,
  Save,
  RotateCcw,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  listPrompts,
  resetPromptOverride,
  savePromptOverride,
  type PromptItem,
} from "@/lib/api";

export default function PromptsSettings() {
  const [list, setList] = useState<PromptItem[] | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [draft, setDraft] = useState<string>("");
  const [original, setOriginal] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const rows = await listPrompts();
      setList(rows);
      return rows;
    } catch (e) {
      setError((e as Error).message);
      return [];
    }
  }, []);

  // Initial load — open the first prompt by default.
  useEffect(() => {
    (async () => {
      const rows = await refresh();
      if (rows.length > 0) setSelectedKey(rows[0].key);
    })();
  }, [refresh]);

  // Sync draft when selection or list changes.
  useEffect(() => {
    if (!list || !selectedKey) {
      setDraft("");
      setOriginal("");
      return;
    }
    const p = list.find((x) => x.key === selectedKey);
    if (p) {
      setDraft(p.current_template);
      setOriginal(p.current_template);
    }
  }, [list, selectedKey]);

  const selected = useMemo(
    () => list?.find((x) => x.key === selectedKey) ?? null,
    [list, selectedKey],
  );

  const dirty = draft !== original;

  const handleSelect = (key: string) => {
    if (dirty && !confirm("Discard unsaved changes?")) return;
    setSelectedKey(key);
    setSavedAt(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!selected || !dirty) return;
    setSaving(true);
    setError(null);
    try {
      await savePromptOverride(selected.key, draft);
      await refresh();
      setOriginal(draft);
      setSavedAt(Date.now());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!selected) return;
    if (
      !confirm(
        `Reset "${selected.name}" to its built-in default? This deletes your custom version.`,
      )
    )
      return;
    setResetting(true);
    setError(null);
    try {
      await resetPromptOverride(selected.key);
      await refresh();
      setSavedAt(Date.now());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setResetting(false);
    }
  };

  const handleRevert = () => {
    setDraft(original);
    setError(null);
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-kpmg-darkBlue">Prompts</h1>
        <p className="text-gray-600">
          Edit the prompts that power each Analyze mode. Overrides take effect
          on the next request — no restart required.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-status-red/40 bg-status-red/5 p-3 text-sm text-status-red">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span className="flex-1 whitespace-pre-wrap">{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-xs underline"
          >
            dismiss
          </button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        {/* ── Left: prompt list ──────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Available prompts</CardTitle>
          </CardHeader>
          <CardContent className="p-2 pt-0">
            {list === null ? (
              <div className="space-y-2 p-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : (
              <ul className="space-y-1">
                {list.map((p) => {
                  const active = p.key === selectedKey;
                  return (
                    <li key={p.key}>
                      <button
                        type="button"
                        onClick={() => handleSelect(p.key)}
                        className={cn(
                          "flex w-full flex-col items-start gap-1 rounded-md px-3 py-2 text-left transition-colors",
                          active
                            ? "bg-kpmg-blue text-white"
                            : "hover:bg-kpmg-lightBlue/40 text-kpmg-darkBlue",
                        )}
                      >
                        <span className="flex w-full items-center gap-2 text-sm font-medium">
                          <span className="flex-1 truncate">{p.name}</span>
                          {p.is_overridden && (
                            <span
                              className={cn(
                                "shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                                active
                                  ? "bg-white/25 text-white"
                                  : "bg-status-yellow/20 text-kpmg-darkBlue",
                              )}
                            >
                              custom
                            </span>
                          )}
                        </span>
                        <span
                          className={cn(
                            "block w-full truncate font-mono text-[11px]",
                            active ? "text-white/70" : "text-gray-500",
                          )}
                        >
                          {p.key}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* ── Right: editor ──────────────────────────────────────────── */}
        <Card>
          <CardContent className="p-6">
            {!selected ? (
              <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
                <Sparkles className="h-10 w-10 text-gray-300" />
                <p className="text-gray-500">
                  Select a prompt on the left to view or edit.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {/* Header */}
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h2 className="text-lg font-semibold text-kpmg-darkBlue">
                        {selected.name}
                      </h2>
                      {selected.is_overridden && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-status-yellow/20 px-2 py-0.5 text-[11px] font-medium text-kpmg-darkBlue">
                          Customised
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-gray-600">
                      {selected.description}
                    </p>
                    <p className="mt-1 font-mono text-[11px] text-gray-400">
                      key: {selected.key}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRevert}
                        disabled={!dirty}
                        title="Revert unsaved edits"
                      >
                        Revert
                      </Button>
                      <Button onClick={handleSave} disabled={!dirty || saving}>
                        {saving ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="h-4 w-4" />
                        )}
                        Save
                      </Button>
                    </div>
                    {selected.is_overridden && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleReset}
                        disabled={resetting}
                        className="text-xs text-gray-500 hover:text-kpmg-blue"
                      >
                        {resetting ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <RotateCcw className="h-3 w-3" />
                        )}
                        Reset to default
                      </Button>
                    )}
                  </div>
                </div>

                {/* Status pill */}
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
                  <span className="text-gray-400">
                    {draft.length.toLocaleString()} chars
                    {selected.is_overridden && selected.updated_at && (
                      <>
                        {" · "}
                        last saved{" "}
                        {new Date(selected.updated_at).toLocaleString()}
                      </>
                    )}
                  </span>
                </div>

                {/* Placeholders chips */}
                <div>
                  <Label className="text-xs uppercase tracking-wider text-gray-500">
                    Required placeholders
                  </Label>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {selected.placeholders.length === 0 ? (
                      <span className="text-xs text-gray-400">
                        None — this prompt has no variables.
                      </span>
                    ) : (
                      selected.placeholders.map((ph) => (
                        <code
                          key={ph}
                          className="rounded bg-kpmg-blue/10 px-2 py-0.5 font-mono text-xs text-kpmg-blue"
                        >
                          {`{${ph}}`}
                        </code>
                      ))
                    )}
                  </div>
                  {selected.placeholders.length > 0 && (
                    <p className="mt-1 text-[11px] text-gray-500">
                      Each must appear somewhere in the template (saving with
                      one missing will fail validation).
                    </p>
                  )}
                </div>

                {/* Editor */}
                <div className="space-y-2">
                  <Label htmlFor="prompt-template">Template</Label>
                  <Textarea
                    id="prompt-template"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    spellCheck={false}
                    className="min-h-[420px] resize-y font-mono text-[13px] leading-relaxed"
                    placeholder="The model's system prompt for this mode…"
                  />
                </div>

                {/* Default reference (collapsible) */}
                {selected.is_overridden && (
                  <details className="rounded-md border border-gray-200 bg-gray-50/60 text-sm">
                    <summary className="cursor-pointer px-3 py-2 font-medium text-gray-600 hover:text-kpmg-darkBlue">
                      Show built-in default ({selected.default_template.length.toLocaleString()} chars)
                    </summary>
                    <pre className="max-h-[300px] overflow-auto rounded-b-md border-t border-gray-200 bg-white px-3 py-2 font-mono text-[12px] leading-relaxed text-gray-700">
                      {selected.default_template}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
