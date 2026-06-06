"use client";

import { useEffect, useState } from "react";

import { EngineStatusView } from "@/components/engine-status/EngineStatusView";

const POLL_INTERVAL_MS = 30_000;

async function fetchHealth(): Promise<boolean> {
  try {
    const r = await fetch("/api/health");
    const d = await r.json();
    return Boolean(d.online);
  } catch {
    return false;
  }
}

export default function EngineStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    // First load: show "checking" (null) until the first response arrives.
    fetchHealth().then(setOnline);

    // Subsequent polls: update silently — never reset to null so there is no
    // "checking" flash on background refreshes.
    const id = setInterval(() => {
      fetchHealth().then(setOnline);
    }, POLL_INTERVAL_MS);

    return () => clearInterval(id);
  }, []);

  return <EngineStatusView online={online} />;
}
