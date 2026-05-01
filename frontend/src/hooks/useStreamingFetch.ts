/**
 * SSE consumer for the FastAPI streaming endpoints.
 *
 * Why fetch + ReadableStream instead of EventSource:
 *   - EventSource is GET-only and can't send a multipart body.
 *   - fetch + getReader gives us the same incremental delivery while
 *     supporting POST + multipart.
 *
 * Line buffering matches the pattern proven in
 * Data-Steward-Assistant/server/ai-provider.ts:244-313 — chunks may split
 * mid-line, so we keep a buffer and only parse complete `\n`-terminated
 * lines. We also strip the SSE `data: ` prefix.
 */
import { useCallback, useRef, useState } from "react";
import type { StreamEvent } from "@/lib/api";

export interface StreamingState {
  status: "idle" | "streaming" | "done" | "error" | "busy";
  text: string;
  events: StreamEvent[];
  error?: string;
  sessionId?: string;
  ttftMs?: number;
  totalMs?: number;
}

const INITIAL: StreamingState = {
  status: "idle",
  text: "",
  events: [],
};

export function useStreamingFetch() {
  const [state, setState] = useState<StreamingState>(INITIAL);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState(INITIAL);
  }, []);

  const start = useCallback(
    async (url: string, body: BodyInit | null, init?: RequestInit) => {
      // Cancel any previous in-flight stream.
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setState({ ...INITIAL, status: "streaming" });

      let textAcc = "";
      const eventsAcc: StreamEvent[] = [];

      try {
        const resp = await fetch(url, {
          method: "POST",
          body,
          signal: ctrl.signal,
          ...init,
        });
        if (!resp.ok || !resp.body) {
          const detail = await resp.text().catch(() => "");
          throw new Error(
            `${resp.status} ${resp.statusText}${detail ? ` — ${detail.slice(0, 200)}` : ""}`,
          );
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });

          // SSE events are separated by blank lines; data lines are prefixed `data: `.
          let nlIdx: number;
          while ((nlIdx = buf.indexOf("\n")) >= 0) {
            const line = buf.slice(0, nlIdx).trimEnd();
            buf = buf.slice(nlIdx + 1);
            if (!line) continue;
            if (!line.startsWith("data:")) continue;
            const json = line.slice(5).trim();
            if (!json) continue;
            let evt: StreamEvent;
            try {
              evt = JSON.parse(json) as StreamEvent;
            } catch {
              continue;
            }
            eventsAcc.push(evt);
            if (evt.type === "token") {
              textAcc += evt.content;
              setState((s) => ({
                ...s,
                text: textAcc,
                events: [...eventsAcc],
              }));
            } else if (evt.type === "session_created") {
              setState((s) => ({ ...s, sessionId: evt.id, events: [...eventsAcc] }));
            } else if (evt.type === "done") {
              setState((s) => ({
                ...s,
                status: "done",
                ttftMs: evt.ttft_ms,
                totalMs: evt.total_ms,
                events: [...eventsAcc],
              }));
              return;
            } else if (evt.type === "busy") {
              setState((s) => ({
                ...s,
                status: "busy",
                error: evt.message,
                events: [...eventsAcc],
              }));
            } else if (evt.type === "error") {
              setState((s) => ({
                ...s,
                status: "error",
                error: evt.message,
                events: [...eventsAcc],
              }));
              return;
            } else {
              // Pass-through for other typed events (compliance mode emits
              // framework_started / narrative_token / scorecard_row /
              // framework_done — consumers read them from `events`).
              setState((s) => ({ ...s, events: [...eventsAcc] }));
            }
          }
        }

        // Stream ended without an explicit `done` — treat as done.
        setState((s) => ({ ...s, status: "done" }));
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setState((s) => ({
          ...s,
          status: "error",
          error: (err as Error).message ?? "Unknown error",
        }));
      }
    },
    [],
  );

  return { ...state, start, reset, abort: () => abortRef.current?.abort() };
}
