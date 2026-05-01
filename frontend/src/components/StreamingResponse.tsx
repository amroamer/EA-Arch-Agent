import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  status: "idle" | "streaming" | "done" | "error" | "busy";
  text: string;
  error?: string;
  ttftMs?: number;
  totalMs?: number;
  /** Apply the pink-bordered "Console View" framing from Slides 7/8. */
  pinkBorder?: boolean;
  className?: string;
}

export function StreamingResponse({
  status,
  text,
  error,
  ttftMs,
  totalMs,
  pinkBorder = false,
  className,
}: Props) {
  const onCopy = () => {
    if (text) navigator.clipboard.writeText(text);
  };

  return (
    <section
      className={cn(
        "rounded-lg bg-white p-6",
        pinkBorder
          ? "border-2 border-kpmg-pink"
          : "border border-gray-200",
        className,
      )}
      aria-live="polite"
      aria-busy={status === "streaming"}
    >
      {/* Status bar */}
      <header className="mb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm">
          {status === "streaming" && (
            <>
              <Loader2 className="h-4 w-4 animate-spin text-kpmg-blue" />
              <span className="text-kpmg-blue">Generating…</span>
            </>
          )}
          {status === "done" && (
            <>
              <CheckCircle2 className="h-4 w-4 text-status-green" />
              <span className="text-status-green">Done</span>
              {totalMs !== undefined && (
                <span className="text-gray-500">
                  • {(totalMs / 1000).toFixed(1)} s
                  {ttftMs !== undefined && ` (TTFT ${(ttftMs / 1000).toFixed(2)} s)`}
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
          {status === "idle" && (
            <span className="text-gray-400">No response yet</span>
          )}
        </div>

        {status === "done" && text && (
          <Button variant="outline" size="sm" onClick={onCopy}>
            <Copy className="h-3.5 w-3.5" />
            Copy markdown
          </Button>
        )}
      </header>

      {/* Body */}
      {text ? (
        <article className="md-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
        </article>
      ) : status === "streaming" ? (
        <div className="space-y-2">
          <div className="h-3 w-2/3 animate-pulse rounded bg-gray-100" />
          <div className="h-3 w-5/6 animate-pulse rounded bg-gray-100" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-gray-100" />
        </div>
      ) : null}
    </section>
  );
}
