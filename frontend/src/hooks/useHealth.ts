import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";

const POLL_MS = 30_000;

export function useHealth(): {
  health: HealthResponse | null;
  error: string | null;
} {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const h = await fetchHealth();
        if (!cancelled) {
          setHealth(h);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    };
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return { health, error };
}
