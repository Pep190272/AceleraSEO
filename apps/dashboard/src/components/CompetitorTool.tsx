"use client";

import { useState, useCallback } from "react";

import { apiFetch } from "@/lib/api";
import { useApiCall } from "@/lib/hooks/useApiCall";
import { useScrollIntoView } from "@/lib/hooks/useScrollIntoView";
import { useT } from "@/lib/i18n";
import type { CompetitorResult } from "@/lib/types/api";
import { CompetitorView } from "@/components/competitors/CompetitorView";

export default function CompetitorTool() {
  const { t, lang } = useT();
  const [domain, setDomain] = useState("");
  const [location, setLocation] = useState("");
  const [expandedDomain, setExpandedDomain] = useState<string | null>(null);
  const [validationError, setValidationError] = useState("");
  const { data: result, loading, error, execute } = useApiCall<CompetitorResult>();
  const { ref: resultRef, trigger: scrollToResult } = useScrollIntoView();

  const run = useCallback(async () => {
    if (!domain.trim()) {
      // Client-side validation must not flip the loading state (no spinner /
      // disabled button flicker), so it bypasses execute and sets the message
      // directly — matching the original inline `setError(...); return;`.
      setValidationError(t("comp.error.nodomain"));
      return;
    }
    setValidationError("");
    setExpandedDomain(null);
    const ok = await execute(() =>
      apiFetch<CompetitorResult>("/api/competitors", {
        method: "POST",
        body: JSON.stringify({ domain: domain.trim(), location, language: lang }),
      })
    );
    if (ok) scrollToResult();
  }, [domain, location, lang, execute, scrollToResult, t]);

  const toggleExpand = useCallback((d: string) => {
    setExpandedDomain((prev) => (prev === d ? null : d));
  }, []);

  return (
    <CompetitorView
      domain={domain}
      location={location}
      result={result}
      expandedDomain={expandedDomain}
      error={validationError || error}
      loading={loading}
      resultRef={resultRef}
      onDomainChange={setDomain}
      onLocationChange={setLocation}
      onRun={run}
      onToggleExpand={toggleExpand}
      t={t}
    />
  );
}
