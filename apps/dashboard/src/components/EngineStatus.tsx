"use client";

import { useEffect, useState } from "react";

export default function EngineStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setOnline(Boolean(d.online)))
      .catch(() => setOnline(false));
  }, []);

  const label =
    online === null ? "checking engine…" : online ? "engine online" : "engine offline";
  const cls = online === null ? "dot" : online ? "dot on" : "dot off";

  return (
    <div className="status">
      <span className={cls} />
      {label}
    </div>
  );
}
