import { Navigate, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import Home from "@/pages/Home";
import Analyze from "@/pages/Analyze";
import Compare from "@/pages/Compare";
import History from "@/pages/History";
import SessionDetail from "@/pages/SessionDetail";
import SettingsLayout from "@/pages/SettingsLayout";
import FrameworkSettings from "@/pages/FrameworkSettings";
import PromptsSettings from "@/pages/PromptsSettings";
import LLMSettings from "@/pages/LLMSettings";
import { COMPARE_ENABLED } from "@/lib/features";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route
          path="/compare"
          element={COMPARE_ENABLED ? <Compare /> : <Navigate to="/" replace />}
        />
        <Route path="/history" element={<History />} />
        <Route path="/history/:id" element={<SessionDetail />} />
        <Route path="/settings" element={<SettingsLayout />}>
          <Route index element={<Navigate to="frameworks" replace />} />
          <Route path="frameworks" element={<FrameworkSettings />} />
          <Route path="frameworks/:id" element={<FrameworkSettings />} />
          <Route path="prompts" element={<PromptsSettings />} />
          <Route path="llm" element={<LLMSettings />} />
        </Route>
        <Route
          path="*"
          element={
            <div className="text-gray-600">Page not found.</div>
          }
        />
      </Route>
    </Routes>
  );
}
