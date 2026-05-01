/**
 * /compare — current vs reference architecture (PRD §5 Phase 5).
 * Renders the response in a pink-bordered box matching Slides 7/8.
 */
import { useMemo, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { ImageUploader } from "@/components/ImageUploader";
import { StreamingResponse } from "@/components/StreamingResponse";
import { useStreamingFetch } from "@/hooks/useStreamingFetch";
import { apiUrl } from "@/lib/api";

export default function Compare() {
  const [current, setCurrent] = useState<File | null>(null);
  const [reference, setReference] = useState<File | null>(null);
  const [userPrompt, setUserPrompt] = useState("");

  const stream = useStreamingFetch();

  const canSubmit = useMemo(
    () =>
      !!current &&
      !!reference &&
      userPrompt.trim().length > 0 &&
      stream.status !== "streaming",
    [current, reference, userPrompt, stream.status],
  );

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || !current || !reference) return;
    const fd = new FormData();
    fd.append("current_image", current);
    fd.append("reference_image", reference);
    fd.append("user_prompt", userPrompt);
    await stream.start(apiUrl("/compare"), fd);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-kpmg-darkBlue">
          Compare Architectural Landscapes
        </h1>
        <p className="text-gray-600">
          Upload the current and reference architectures, describe what you
          want compared, and get a structured gap analysis + implementation
          roadmap.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form className="space-y-6" onSubmit={onSubmit}>
            <div className="grid gap-6 md:grid-cols-2">
              <ImageUploader
                label="Current Architecture"
                file={current}
                onChange={setCurrent}
              />
              <ImageUploader
                label="Reference Architecture"
                file={reference}
                onChange={setReference}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="compare-prompt">
                What should we compare?{" "}
                <span className="text-status-red">*</span>
              </Label>
              <Textarea
                id="compare-prompt"
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                placeholder="Compare the current state architecture with the reference architecture based on: 1) Private endpoints 2) Public endpoints 3) IAM 4) Secrets management…"
                className="min-h-[140px]"
              />
            </div>

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={!canSubmit}>
                {stream.status === "streaming" ? "Generating…" : "Compare"}
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

      {stream.status !== "idle" && (
        <StreamingResponse
          status={stream.status}
          text={stream.text}
          error={stream.error}
          ttftMs={stream.ttftMs}
          totalMs={stream.totalMs}
          pinkBorder
        />
      )}
    </div>
  );
}
