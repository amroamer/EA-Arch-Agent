import { NavLink } from "react-router-dom";
import { Home, ScanSearch, GitCompare, History, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { COMPARE_ENABLED } from "@/lib/features";

const NAV = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/analyze", label: "Analyze", icon: ScanSearch, end: false },
  ...(COMPARE_ENABLED
    ? [{ to: "/compare", label: "Compare", icon: GitCompare, end: false }]
    : []),
  { to: "/history", label: "History", icon: History, end: false },
  { to: "/settings/frameworks", label: "Settings", icon: Settings, end: false },
];

export function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 border-r border-gray-200 bg-white md:block">
      <nav className="flex flex-col gap-1 p-4" aria-label="Primary">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium",
                "transition-colors",
                isActive
                  ? "bg-kpmg-blue text-white"
                  : "text-gray-700 hover:bg-kpmg-lightBlue/40 hover:text-kpmg-darkBlue",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
