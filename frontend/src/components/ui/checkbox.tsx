import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface CheckboxProps {
  checked: boolean;
  onCheckedChange: (next: boolean) => void;
  id?: string;
  disabled?: boolean;
  className?: string;
}

export const Checkbox = React.forwardRef<HTMLButtonElement, CheckboxProps>(
  ({ checked, onCheckedChange, id, disabled, className }, ref) => (
    <button
      ref={ref}
      id={id}
      type="button"
      role="checkbox"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange(!checked)}
      className={cn(
        "h-4 w-4 shrink-0 rounded border border-gray-400 bg-white",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-kpmg-cobalt focus-visible:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        checked && "bg-kpmg-blue border-kpmg-blue",
        "flex items-center justify-center transition-colors",
        className,
      )}
    >
      {checked && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
    </button>
  ),
);
Checkbox.displayName = "Checkbox";
