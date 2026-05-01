import { Link } from "react-router-dom";
import { useHealth } from "@/hooks/useHealth";
import { cn } from "@/lib/utils";
import { Switch as ConsoleToggle } from "./ConsoleToggle";

/**
 * Top app bar — KPMG-branded.
 *  - Logo + product title
 *  - Console-View toggle (matches Slides 7/8 — purely visual mode flag for v1)
 *  - Health dot (green/yellow/red) reflecting Ollama + DB status
 */
export function Header({
  consoleView,
  onToggleConsoleView,
}: {
  consoleView: boolean;
  onToggleConsoleView: (next: boolean) => void;
}) {
  const { health } = useHealth();

  const dotClass = (() => {
    if (!health) return "bg-gray-400";
    if (health.status === "ok") return "bg-status-green";
    if (health.status === "degraded") return "bg-status-yellow";
    return "bg-status-red";
  })();

  const dotLabel = (() => {
    if (!health) return "Status: connecting…";
    if (health.status === "ok") return "All systems operational";
    if (health.status === "degraded")
      return `Degraded: ${health.error ?? "see /health"}`;
    return `Down: ${health.error ?? "see /health"}`;
  })();

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="flex h-16 w-full items-center gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt rounded-md"
        >
          <img
            src="/arch-assistant/kpmg-logo.svg"
            alt="KPMG"
            className="h-8 w-auto"
          />
          <div className="flex flex-col leading-tight">
            <span className="text-base font-semibold text-kpmg-blue">
              EA Arch Agent
            </span>
            <span className="text-xs text-gray-500">
              Enterprise Architecture Compliance Reviewer
            </span>
          </div>
        </Link>

        <div className="ml-auto flex items-center gap-4">
          <ConsoleToggle
            checked={consoleView}
            onCheckedChange={onToggleConsoleView}
          />

          <div
            className="flex items-center gap-2"
            title={dotLabel}
            aria-label={dotLabel}
          >
            <span
              className={cn(
                "inline-block h-2.5 w-2.5 rounded-full",
                dotClass,
                health?.status === "down" && "animate-pulse-slow",
              )}
            />
            <span className="hidden text-xs text-gray-500 md:inline">
              {health?.status ?? "…"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}

