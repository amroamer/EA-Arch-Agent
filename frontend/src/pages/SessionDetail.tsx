import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ImageOff } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StreamingResponse } from "@/components/StreamingResponse";
import { SavedScorecardsView } from "@/components/ComplianceScorecards";
import { getSession, imageUrl, type SessionDetail as Detail } from "@/lib/api";

/** Renders an uploaded session image with a label. Falls back gracefully
 *  if the hash is missing (older sessions from before image storage)
 *  or the bytes have been pruned. */
function SessionImage({
  hash,
  label,
}: {
  hash: string | null;
  label: string;
}) {
  const [failed, setFailed] = useState(false);

  if (!hash) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-2 p-6 text-gray-400">
          <ImageOff className="h-6 w-6" />
          <span className="text-xs">{label} — image not stored</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="space-y-2 p-3">
        <div className="text-xs font-medium uppercase tracking-wide text-gray-500">
          {label}
        </div>
        {failed ? (
          <div className="flex flex-col items-center justify-center gap-2 py-8 text-gray-400">
            <ImageOff className="h-6 w-6" />
            <span className="text-xs">Image bytes no longer available</span>
          </div>
        ) : (
          <a
            href={imageUrl(hash)}
            target="_blank"
            rel="noreferrer"
            className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt rounded-md"
          >
            <img
              src={imageUrl(hash)}
              alt={label}
              className="max-h-96 w-full rounded-md border border-gray-200 object-contain bg-gray-50"
              onError={() => setFailed(true)}
              loading="lazy"
            />
          </a>
        )}
        <div className="text-[11px] text-gray-400 font-mono truncate">
          sha256 {hash.slice(0, 16)}…
        </div>
      </CardContent>
    </Card>
  );
}

export default function SessionDetail() {
  const { id = "" } = useParams<{ id: string }>();
  const [session, setSession] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await getSession(id);
        if (!cancelled) setSession(s);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="space-y-4">
      <Button asChild variant="ghost" size="sm">
        <Link to="/history">
          <ArrowLeft className="h-4 w-4" /> Back to history
        </Link>
      </Button>

      {error && <p className="text-status-red">{error}</p>}
      {!session && !error && <Skeleton className="h-48 w-full" />}

      {session && (
        <>
          <div>
            <h1 className="text-2xl font-bold text-kpmg-darkBlue capitalize">
              {session.session_type}
              {session.mode ? ` · ${session.mode}` : ""}
              {session.persona ? ` · ${session.persona}` : ""}
            </h1>
            <p className="text-sm text-gray-500">
              {new Date(session.created_at).toLocaleString()}
              {session.total_ms !== null && (
                <> · {(session.total_ms / 1000).toFixed(1)} s</>
              )}
            </p>
          </div>

          {/* Uploaded images */}
          {session.session_type === "compare" ? (
            <div className="grid gap-4 md:grid-cols-2">
              <SessionImage
                hash={session.image_hash}
                label="Current Architecture"
              />
              <SessionImage
                hash={session.reference_image_hash}
                label="Reference Architecture"
              />
            </div>
          ) : (
            <SessionImage
              hash={session.image_hash}
              label="Architecture diagram"
            />
          )}

          {session.user_prompt && (
            <Card>
              <CardContent className="p-4">
                <h2 className="mb-1 text-sm font-medium text-kpmg-darkBlue">
                  Prompt
                </h2>
                <p className="whitespace-pre-wrap text-sm text-gray-700">
                  {session.user_prompt}
                </p>
              </CardContent>
            </Card>
          )}

          {session.mode === "compliance" && session.scorecards ? (
            <SavedScorecardsView scorecards={session.scorecards} />
          ) : (
            <StreamingResponse
              status={session.status === "error" ? "error" : "done"}
              text={session.response_markdown ?? ""}
              error={session.error_message ?? undefined}
              ttftMs={session.ttft_ms ?? undefined}
              totalMs={session.total_ms ?? undefined}
              pinkBorder={session.session_type === "compare"}
            />
          )}
        </>
      )}
    </div>
  );
}
