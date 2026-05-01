import { Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * "Console View" toggle from Slides 7/8.
 * Visual flag for v1 — applies a slightly more compact, monospaced
 * rendering style (handled at the page level).
 */
export function Switch({
  checked,
  onCheckedChange,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-gray-300 px-3 py-1.5 text-xs font-medium transition-colors",
        "hover:border-kpmg-blue hover:text-kpmg-blue",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt focus-visible:ring-offset-2",
        checked
          ? "bg-kpmg-darkBlue text-white border-kpmg-darkBlue"
          : "bg-white text-gray-600",
      )}
    >
      <Terminal className="h-3.5 w-3.5" />
      Console View
    </button>
  );
}
