/**
 * /analyze — single-image analysis with 5 modes (PRD §5 Phase 4 + Compliance).
 *
 * Modes:
 *   - quick        : no extra inputs
 *   - detailed     : optional focus-area checkboxes
 *   - persona      : required persona dropdown
 *   - user_driven  : required user prompt textarea
 *   - compliance   : pick ≥1 EA Compliance Framework; per-framework scorecards
 */
import { useEffect, useMemo, useState } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ImageUploader } from "@/components/ImageUploader";
import { StreamingResponse } from "@/components/StreamingResponse";
import { ComplianceScorecards } from "@/components/ComplianceScorecards";
import { useStreamingFetch } from "@/hooks/useStreamingFetch";
import {
  apiUrl,
  listFrameworks,
  type AnalysisMode,
  type FrameworkSummary,
  type Persona,
} from "@/lib/api";

const FOCUS_OPTIONS: { value: string; label: string }[] = [
  { value: "Network", label: "Network" },
  { value: "Security", label: "Security" },
  { value: "Infrastructure", label: "Infrastructure" },
  { value: "Performance", label: "Performance" },
  { value: "Cost", label: "Cost" },
];

const PERSONA_OPTIONS: { value: Persona; label: string }[] = [
  { value: "data", label: "Data Architect" },
  { value: "network", label: "Network Architect" },
  { value: "security", label: "Security Architect" },
  { value: "enterprise", label: "Enterprise Architect" },
];

export default function Analyze() {
  const [mode, setMode] = useState<AnalysisMode>("quick");
  const [image, setImage] = useState<File | null>(null);
  const [persona, setPersona] = useState<Persona | "">("");
  const [focus, setFocus] = useState<Set<string>>(new Set());
  const [userPrompt, setUserPrompt] = useState("");
  const [frameworks, setFrameworks] = useState<FrameworkSummary[] | null>(null);
  const [selectedFrameworkIds, setSelectedFrameworkIds] = useState<Set<string>>(
    new Set(),
  );

  const stream = useStreamingFetch();

  // Lazy-load frameworks the first time the user opens the Compliance tab.
  useEffect(() => {
    if (mode !== "compliance" || frameworks !== null) return;
    let cancelled = false;
    listFrameworks()
      .then((rows) => {
        if (!cancelled) setFrameworks(rows);
      })
      .catch(() => {
        if (!cancelled) setFrameworks([]);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, frameworks]);

  const canSubmit = useMemo(() => {
    if (!image) return false;
    if (stream.status === "streaming") return false;
    if (mode === "persona" && !persona) return false;
    if (mode === "user_driven" && !userPrompt.trim()) return false;
    if (mode === "compliance" && selectedFrameworkIds.size === 0) return false;
    return true;
  }, [image, mode, persona, userPrompt, selectedFrameworkIds, stream.status]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !image) return;
    const fd = new FormData();
    fd.append("image", image);
    fd.append("mode", mode);
    if (mode === "persona" && persona) fd.append("persona", persona);
    if (mode === "detailed" && focus.size > 0)
      fd.append("focus_areas", Array.from(focus).join(","));
    if (mode === "user_driven") fd.append("user_prompt", userPrompt);
    if (mode === "compliance") {
      fd.append("framework_ids", Array.from(selectedFrameworkIds).join(","));
    }
    await stream.start(apiUrl("/analyze"), fd);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-kpmg-darkBlue">
          Analyze Current State Architecture
        </h1>
        <p className="text-gray-600">
          Upload a single architecture diagram and choose an analysis mode.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form className="space-y-6" onSubmit={onSubmit}>
            {/* Mode selector */}
            <Tabs value={mode} onValueChange={(v) => setMode(v as AnalysisMode)}>
              <TabsList>
                <TabsTrigger value="quick">Quick</TabsTrigger>
                <TabsTrigger value="detailed">Detailed</TabsTrigger>
                <TabsTrigger value="persona">Persona-Based</TabsTrigger>
                <TabsTrigger value="user_driven">User-Driven</TabsTrigger>
                <TabsTrigger value="compliance">Compliance</TabsTrigger>
              </TabsList>

              <TabsContent value="quick">
                <p className="text-sm text-gray-600">
                  Fast, high-level review — strengths, top concerns, and
                  recommended next steps. Best as a starting point.
                </p>
              </TabsContent>

              <TabsContent value="detailed">
                <div className="space-y-3">
                  <p className="text-sm text-gray-600">
                    Deep-dive across Security, Availability, Scalability,
                    Performance, Cost, and Operational Excellence. Optionally
                    bias the analysis toward specific focus areas:
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {FOCUS_OPTIONS.map((f) => {
                      const id = `focus-${f.value}`;
                      const checked = focus.has(f.value);
                      return (
                        <label
                          key={f.value}
                          htmlFor={id}
                          className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 px-3 py-1.5 text-sm hover:bg-gray-50"
                        >
                          <Checkbox
                            id={id}
                            checked={checked}
                            onCheckedChange={(next) => {
                              setFocus((prev) => {
                                const out = new Set(prev);
                                if (next) out.add(f.value);
                                else out.delete(f.value);
                                return out;
                              });
                            }}
                          />
                          {f.label}
                        </label>
                      );
                    })}
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="persona">
                <div className="space-y-2">
                  <Label htmlFor="persona-select">
                    Persona <span className="text-status-red">*</span>
                  </Label>
                  <Select
                    value={persona}
                    onValueChange={(v) => setPersona(v as Persona)}
                  >
                    <SelectTrigger id="persona-select" className="max-w-sm">
                      <SelectValue placeholder="Choose a persona…" />
                    </SelectTrigger>
                    <SelectContent>
                      {PERSONA_OPTIONS.map((p) => (
                        <SelectItem key={p.value} value={p.value}>
                          {p.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </TabsContent>

              <TabsContent value="user_driven">
                <div className="space-y-2">
                  <Label htmlFor="user-prompt">
                    Your question <span className="text-status-red">*</span>
                  </Label>
                  <Textarea
                    id="user-prompt"
                    value={userPrompt}
                    onChange={(e) => setUserPrompt(e.target.value)}
                    placeholder="As a cloud architect, find the anomalies in this architecture based on the following design principles…"
                    className="min-h-[120px]"
                  />
                </div>
              </TabsContent>

              <TabsContent value="compliance">
                <div className="space-y-3">
                  <p className="text-sm text-gray-600">
                    Score the architecture against one or more EA Compliance
                    Frameworks. Each framework produces its own narrative
                    critique and a filled scorecard you can edit before saving.
                  </p>
                  <div>
                    <div className="flex items-center justify-between gap-3">
                      <Label>
                        Frameworks <span className="text-status-red">*</span>
                        {frameworks && frameworks.length > 0 && (
                          <span className="ml-2 text-xs font-normal text-gray-500">
                            {selectedFrameworkIds.size} of {frameworks.length}{" "}
                            selected
                          </span>
                        )}
                      </Label>
                      {frameworks && frameworks.length > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            const allSelected =
                              selectedFrameworkIds.size === frameworks.length;
                            setSelectedFrameworkIds(
                              allSelected
                                ? new Set()
                                : new Set(frameworks.map((f) => f.id)),
                            );
                          }}
                          className="text-xs font-medium text-kpmg-blue hover:text-kpmg-cobalt hover:underline"
                        >
                          {selectedFrameworkIds.size === frameworks.length
                            ? "Clear all"
                            : "Select all"}
                        </button>
                      )}
                    </div>
                    {frameworks === null ? (
                      <p className="mt-2 text-sm text-gray-400">
                        Loading frameworks…
                      </p>
                    ) : frameworks.length === 0 ? (
                      <p className="mt-2 text-sm text-gray-500">
                        No frameworks defined yet. Go to <strong>Settings</strong>{" "}
                        → <strong>EA Compliance Framework</strong> to create one.
                      </p>
                    ) : (
                      <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                        {frameworks.map((fw) => {
                          const id = `fw-${fw.id}`;
                          const checked = selectedFrameworkIds.has(fw.id);
                          return (
                            <label
                              key={fw.id}
                              htmlFor={id}
                              className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-gray-200 px-3 py-2 text-sm hover:bg-gray-50"
                            >
                              <Checkbox
                                id={id}
                                checked={checked}
                                onCheckedChange={(next) => {
                                  setSelectedFrameworkIds((prev) => {
                                    const out = new Set(prev);
                                    if (next) out.add(fw.id);
                                    else out.delete(fw.id);
                                    return out;
                                  });
                                }}
                              />
                              <span className="flex-1 truncate">
                                {fw.name}
                              </span>
                              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[11px] text-gray-600">
                                {fw.item_count}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Image uploader */}
            <ImageUploader
              label="Architecture diagram"
              file={image}
              onChange={setImage}
            />

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={!canSubmit}>
                {stream.status === "streaming" ? "Generating…" : "Analyze"}
              </Button>
              {stream.status !== "idle" && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => stream.reset()}
                >
                  Reset
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {stream.status !== "idle" &&
        (mode === "compliance" ? (
          <ComplianceScorecards
            status={stream.status}
            error={stream.error}
            sessionId={stream.sessionId}
            events={stream.events}
            ttftMs={stream.ttftMs}
            totalMs={stream.totalMs}
          />
        ) : (
          <StreamingResponse
            status={stream.status}
            text={stream.text}
            error={stream.error}
            ttftMs={stream.ttftMs}
            totalMs={stream.totalMs}
          />
        ))}
    </div>
  );
}
