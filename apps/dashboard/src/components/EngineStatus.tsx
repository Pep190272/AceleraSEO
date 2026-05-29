"use client";

import { useEffect, useState } from "react";

import { useT } from "@/lib/i18n";

export default function EngineStatus() {
  const { t } = useT();
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setOnline(Boolean(d.online)))
      .catch(() => setOnline(false));
  }, []);

  const label =
    online === null ? t("engine.checking") : online ? t("engine.online") : t("engine.offline");
  const cls = online === null ? "dot" : online ? "dot on" : "dot off";

  return (
    <div className="status">
      <span className={cls} />
      {label}
    </div>
  );
}
