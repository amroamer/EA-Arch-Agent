import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSessions, type SessionListItem } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { ScanSearch, GitCompare, AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { COMPARE_ENABLED } from "@/lib/features";

const REFRESH_MS = 5_000;

function StatusIcon({ status }: { status: SessionListItem["status"] }) {
  if (status === "running")
    return <Loader2 className="h-4 w-4 animate-spin text-kpmg-blue" />;
  if (status === "done")
    return <CheckCircle2 className="h-4 w-4 text-status-green" />;
  return <AlertTriangle className="h-4 w-4 text-status-red" />;
}

function TypeIcon({ type }: { type: SessionListItem["session_type"] }) {
  if (type === "compare")
    return <GitCompare className="h-4 w-4 text-kpmg-purple" />;
  return <ScanSearch className="h-4 w-4 text-kpmg-blue" />;
}

export function HistoryList({
  refreshKey,
  inline = false,
}: {
  refreshKey?: number;
  inline?: boolean;
}) {
  const [items, setItems] = useState<SessionListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const rows = await listSessions(50, 0);
        if (!cancelled) {
          setItems(rows);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    tick();
    const id = setInterval(tick, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [refreshKey]);

  // Filter out compare sessions when the feature is hidden in the UI.
  const visible = !COMPARE_ENABLED && items
    ? items.filter((s) => s.session_type !== "compare")
    : items;

  if (error) {
    return (
      <p className="text-sm text-status-red">
        Could not load history: {error}
      </p>
    );
  }
  if (visible === null) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-12 w-full" />
      </div>
    );
  }
  if (visible.length === 0) {
    return (
      <p className="text-sm text-gray-500">
        {COMPARE_ENABLED
          ? "No past sessions yet — run an Analyze or Compare to populate history."
          : "No past sessions yet — run an Analyze to populate history."}
      </p>
    );
  }

  return (
    <ul className={inline ? "divide-y divide-gray-100" : "space-y-2"}>
      {visible.map((s) => (
        <li key={s.id}>
          <Link
            to={`/history/${s.id}`}
            className="flex items-center gap-3 rounded-md p-3 hover:bg-kpmg-lightBlue/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt"
          >
            <TypeIcon type={s.session_type} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-sm font-medium text-kpmg-darkBlue">
                <span className="capitalize">{s.session_type}</span>
                {s.mode && (
                  <span className="rounded bg-kpmg-lightBlue/40 px-1.5 py-0.5 text-xs text-kpmg-darkBlue">
                    {s.mode}
                  </span>
                )}
                {s.persona && (
                  <span className="rounded bg-kpmg-lightBlue/40 px-1.5 py-0.5 text-xs text-kpmg-darkBlue">
                    {s.persona}
                  </span>
                )}
              </div>
              <p className="truncate text-xs text-gray-500">
                {s.prompt_preview ?? "—"}
              </p>
            </div>
            <div className="flex flex-col items-end gap-1 text-xs text-gray-400">
              <StatusIcon status={s.status} />
              <span>{new Date(s.created_at).toLocaleString()}</span>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
