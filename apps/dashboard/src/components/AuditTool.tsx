"use client";

import { useState, useCallback } from "react";

import { useT } from "@/lib/i18n";
import { apiFetch } from "@/lib/api";
import { useApiCall } from "@/lib/hooks/useApiCall";
import type { Report } from "@/lib/types/api";
import AuditView from "@/components/audit/AuditView";

export default function AuditTool() {
  const { t } = useT();
  const [url, setUrl] = useState("https://example.com");
  const { data: report, loading, error, execute } = useApiCall<Report>();

  const run = useCallback(() => {
    execute(() =>
      apiFetch<Report>("/api/audit", {
        method: "POST",
        body: JSON.stringify({ startUrl: url, maxPages: 25 }),
      })
    );
  }, [execute, url]);

  return (
    <AuditView
      url={url}
      loading={loading}
      error={error}
      report={report}
      onUrlChange={setUrl}
      onRun={run}
      t={t}
    />
  );
}
