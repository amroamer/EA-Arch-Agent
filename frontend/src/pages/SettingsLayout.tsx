/**
 * Settings — top-level layout with sub-nav tabs.
 *
 *   /settings              → redirects to /settings/frameworks
 *   /settings/frameworks   → EA Compliance Framework editor
 *   /settings/prompts      → Prompts editor
 *
 * The sidebar's "Settings" entry routes to /settings; this layout renders
 * the tabs and an <Outlet> for the active sub-page.
 */
import { NavLink, Outlet } from "react-router-dom";
import { ListChecks, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  {
    to: "/settings/frameworks",
    label: "Frameworks",
    icon: ListChecks,
  },
  {
    to: "/settings/prompts",
    label: "Prompts",
    icon: Sparkles,
  },
];

export default function SettingsLayout() {
  return (
    <div className="space-y-4">
      {/* Sub-nav tabs */}
      <nav
        className="flex gap-1 border-b border-gray-200"
        aria-label="Settings sections"
      >
        {TABS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "inline-flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-kpmg-blue text-kpmg-blue"
                  : "border-transparent text-gray-500 hover:border-gray-300 hover:text-kpmg-darkBlue",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div>
        <Outlet />
      </div>
    </div>
  );
}
