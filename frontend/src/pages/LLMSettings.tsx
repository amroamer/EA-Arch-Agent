/**
 * Settings → LLM Model.
 *
 *  Top card  : pick the model from Ollama's catalogue + show its size /
 *              parameter count / quantization level. The chosen model is
 *              saved to the singleton `llm_config` row and used by every
 *              analyze/compare/compliance call.
 *  Bottom card: tweak the sampling knobs — temperature, context window,
 *              prediction budget, top_p / top_k / repeat_penalty / seed,
 *              and Ollama keep_alive.
 *
 * Optional knobs (top_p, top_k, repeat_penalty, seed) can be left blank;
 * blank means "use Ollama's default".
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Cpu,
  RefreshCw,
  Sliders,
  Info,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  getLLMConfig,
  listLLMModels,
  saveLLMConfig,
  type LLMConfigBody,
  type LLMConfigData,
  type LLMModel,
} from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────────

function formatBytes(b: number): string {
  if (!b || b <= 0) return "—";
  if (b > 1024 ** 3) return `${(b / 1024 ** 3).toFixed(1)} GB`;
  if (b > 1024 ** 2) return `${(b / 1024 ** 2).toFixed(1)} MB`;
  return `${(b / 1024).toFixed(0)} KB`;
}

/** Defaults used when no config row exists. Mirror the backend's
 *  `LLMConfigBody` Pydantic defaults. */
function emptyBody(modelName: string): LLMConfigBody {
  return {
    model: modelName,
    temperature: 0.2,
    num_ctx: 16_384,
    num_predict: 4096,
    top_p: null,
    top_k: null,
    repeat_penalty: null,
    seed: null,
    keep_alive: "-1",
  };
}

/** Parse a number-or-blank input. Blank → null (use Ollama default). */
function parseOptionalNumber(s: string): number | null {
  const trimmed = s.trim();
  if (trimmed === "") return null;
  const v = Number(trimmed);
  return Number.isFinite(v) ? v : null;
}

/** Show null as empty string, otherwise show the number. */
function fmtOptional(v: number | null): string {
  return v === null || v === undefined ? "" : String(v);
}

// ── Page ───────────────────────────────────────────────────────────────

export default function LLMSettings() {
  const [models, setModels] = useState<LLMModel[] | null>(null);
  const [config, setConfig] = useState<LLMConfigData | null>(null);
  const [draft, setDraft] = useState<LLMConfigBody | null>(null);
  const [saving, setSaving] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    setReloading(true);
    try {
      const [m, c] = await Promise.all([listLLMModels(), getLLMConfig()]);
      setModels(m);
      setConfig(c);
      setDraft({
        model: c.model,
        temperature: c.temperature,
        num_ctx: c.num_ctx,
        num_predict: c.num_predict,
        top_p: c.top_p,
        top_k: c.top_k,
        repeat_penalty: c.repeat_penalty,
        seed: c.seed,
        keep_alive: c.keep_alive,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReloading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const dirty = useMemo(() => {
    if (!config || !draft) return false;
    return (
      draft.model !== config.model ||
      draft.temperature !== config.temperature ||
      draft.num_ctx !== config.num_ctx ||
      draft.num_predict !== config.num_predict ||
      draft.top_p !== config.top_p ||
      draft.top_k !== config.top_k ||
      draft.repeat_penalty !== config.repeat_penalty ||
      draft.seed !== config.seed ||
      draft.keep_alive !== config.keep_alive
    );
  }, [config, draft]);

  const onSave = useCallback(async () => {
    if (!draft) return;
    setError(null);
    setSaving(true);
    try {
      const updated = await saveLLMConfig(draft);
      setConfig(updated);
      setSavedAt(Date.now());
      // Auto-clear the saved indicator after a few seconds.
      setTimeout(() => setSavedAt(null), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }, [draft]);

  const onResetDraft = useCallback(() => {
    if (!config) return;
    setDraft(emptyBody(config.model));
  }, [config]);

  const selectedModel = useMemo(() => {
    if (!models || !draft) return null;
    return models.find((m) => m.name === draft.model) ?? null;
  }, [models, draft]);

  // ── Render ───────────────────────────────────────────────────────────

  if (!config || !draft || !models) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* ── Header row ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-xl font-semibold text-kpmg-darkBlue">
            LLM Model & Sampling
          </h2>
          <p className="text-sm text-gray-500">
            Pick the Ollama model and tune the generation parameters used by
            every Analyze, Compare, and Compliance call.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refresh}
            disabled={reloading || saving}
            className="text-kpmg-darkBlue"
          >
            {reloading ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-1 h-4 w-4" />
            )}
            Reload
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {savedAt && !dirty && (
        <div className="flex items-center gap-2 rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          <CheckCircle2 className="h-4 w-4" />
          <span>Saved. New analyses will use these settings.</span>
        </div>
      )}

      {/* ── Model selection ────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-kpmg-darkBlue">
            <Cpu className="h-4 w-4" />
            Default model
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <Select
              value={draft.model}
              onValueChange={(value) =>
                setDraft({ ...draft, model: value })
              }
            >
              <SelectTrigger id="model">
                <SelectValue placeholder="Select a model" />
              </SelectTrigger>
              <SelectContent>
                {models.length === 0 ? (
                  <div className="px-2 py-3 text-sm text-gray-500">
                    No models found on the configured Ollama daemon.
                  </div>
                ) : (
                  models.map((m) => (
                    <SelectItem key={m.name} value={m.name}>
                      <span className="font-medium">{m.name}</span>
                      <span className="ml-2 text-xs text-gray-500">
                        {m.parameter_size ?? ""}
                        {m.quantization ? ` · ${m.quantization}` : ""}
                        {m.size_bytes
                          ? ` · ${formatBytes(m.size_bytes)}`
                          : ""}
                      </span>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>

            {/* If the user typed (or saved) a model name not in the
                catalogue, surface that — otherwise the selected row will
                appear blank. */}
            {!selectedModel && (
              <p className="text-xs text-amber-600">
                The selected model{" "}
                <code className="rounded bg-amber-50 px-1">
                  {draft.model}
                </code>{" "}
                isn&apos;t in the catalogue. Either pull it on the Ollama
                host or pick another from the dropdown.
              </p>
            )}
          </div>

          {selectedModel && (
            <div className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
              <Stat label="Family" value={selectedModel.family ?? "—"} />
              <Stat
                label="Parameters"
                value={selectedModel.parameter_size ?? "—"}
              />
              <Stat
                label="Quantization"
                value={selectedModel.quantization ?? "—"}
              />
              <Stat
                label="On-disk"
                value={formatBytes(selectedModel.size_bytes)}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Sampling parameters ────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-kpmg-darkBlue">
            <Sliders className="h-4 w-4" />
            Sampling parameters
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Required block */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field
              label="Temperature"
              hint="0 = deterministic, 1 = creative. Compliance scoring works best at 0.1–0.3."
            >
              <Input
                type="number"
                step="0.05"
                min="0"
                max="2"
                value={draft.temperature}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    temperature: Number(e.target.value),
                  })
                }
              />
            </Field>

            <Field
              label="Context window (num_ctx)"
              hint="Tokens of prompt + history the model sees. qwen2.5vl maxes at 32 768."
            >
              <Input
                type="number"
                step="512"
                min="512"
                max="131072"
                value={draft.num_ctx}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    num_ctx: Number(e.target.value),
                  })
                }
              />
            </Field>

            <Field
              label="Max tokens to generate (num_predict)"
              hint="Cap on the model's output length. -1 means no cap."
            >
              <Input
                type="number"
                step="256"
                min="-1"
                max="131072"
                value={draft.num_predict}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    num_predict: Number(e.target.value),
                  })
                }
              />
            </Field>

            <Field
              label="Keep-alive"
              hint='"-1" pins the model in VRAM, "30m" unloads after idle, "0" unloads immediately.'
            >
              <Input
                value={draft.keep_alive}
                onChange={(e) =>
                  setDraft({ ...draft, keep_alive: e.target.value })
                }
                placeholder="-1"
              />
            </Field>
          </div>

          {/* Optional sampling block */}
          <div>
            <div className="mb-3 flex items-center gap-2 text-xs text-gray-500">
              <Info className="h-3.5 w-3.5" />
              <span>
                Optional knobs — leave blank to use Ollama&apos;s default.
              </span>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Field
                label="top_p"
                hint="Nucleus sampling (0 – 1). Lower = more focused output."
              >
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={fmtOptional(draft.top_p)}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      top_p: parseOptionalNumber(e.target.value),
                    })
                  }
                />
              </Field>

              <Field
                label="top_k"
                hint="Sample from the top-K tokens. Common range 20 – 100."
              >
                <Input
                  type="number"
                  step="1"
                  min="1"
                  max="10000"
                  value={fmtOptional(draft.top_k)}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      top_k: parseOptionalNumber(e.target.value),
                    })
                  }
                />
              </Field>

              <Field
                label="repeat_penalty"
                hint="Penalise repeated tokens. 1.0 = off, 1.1 – 1.2 typical."
              >
                <Input
                  type="number"
                  step="0.05"
                  min="0.5"
                  max="2"
                  value={fmtOptional(draft.repeat_penalty)}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      repeat_penalty: parseOptionalNumber(e.target.value),
                    })
                  }
                />
              </Field>

              <Field
                label="seed"
                hint="Fixed integer for reproducible runs. Blank = random per call."
              >
                <Input
                  type="number"
                  step="1"
                  value={fmtOptional(draft.seed)}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      seed: parseOptionalNumber(e.target.value),
                    })
                  }
                />
              </Field>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Footer actions ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs text-gray-500">
          {config.is_overridden ? (
            <span>
              Saved override active
              {config.updated_at && (
                <>
                  {" "}
                  · last updated{" "}
                  {new Date(config.updated_at).toLocaleString()}
                </>
              )}
            </span>
          ) : (
            <span>Using built-in defaults — no row saved yet.</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onResetDraft}
            disabled={saving}
            className="text-kpmg-darkBlue"
          >
            Reset to defaults
          </Button>
          <Button
            size="sm"
            onClick={onSave}
            disabled={saving || !dirty}
            className={cn(
              "bg-kpmg-blue text-white hover:bg-kpmg-darkBlue",
              !dirty && "opacity-60",
            )}
          >
            {saving ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-1 h-4 w-4" />
            )}
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}

// ── Tiny helper components ─────────────────────────────────────────────

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-0.5">
      <div className="uppercase tracking-wide text-gray-500">{label}</div>
      <div className="font-medium text-kpmg-darkBlue">{value}</div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
      {hint && <p className="text-xs text-gray-500">{hint}</p>}
    </div>
  );
}
