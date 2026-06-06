"use client";

import { useT } from "@/lib/i18n";

interface EngineStatusViewProps {
  online: boolean | null;
}

export function EngineStatusView({ online }: EngineStatusViewProps) {
  const { t } = useT();

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
