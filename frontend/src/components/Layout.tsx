import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

/** Top-level chrome: header + sidebar + outlet. */
export function Layout() {
  const [consoleView, setConsoleView] = useState(false);
  return (
    <div className="flex min-h-screen flex-col">
      <Header
        consoleView={consoleView}
        onToggleConsoleView={setConsoleView}
      />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main
          className={`flex-1 overflow-auto ${consoleView ? "font-mono text-[13.5px]" : ""}`}
        >
          <div className="w-full px-4 py-4 sm:px-6 sm:py-5 lg:px-8 lg:py-6">
            <Outlet context={{ consoleView }} />
          </div>
        </main>
      </div>
    </div>
  );
}
