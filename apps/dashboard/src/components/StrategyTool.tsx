"use client";

import { useState, useCallback } from "react";

import { useT } from "@/lib/i18n";
import { apiFetch } from "@/lib/api";
import { useApiCall } from "@/lib/hooks/useApiCall";
import { useScrollIntoView } from "@/lib/hooks/useScrollIntoView";
import type { Plan } from "@/lib/types/api";
import StrategyView, { SAMPLE, parseKeywords } from "@/components/strategy/StrategyView";

export default function StrategyTool() {
  const { lang } = useT();
  const [mode, setMode] = useState<"discover" | "paste">("discover");
  const [maturity, setMaturity] = useState(8);
  const [isLocal, setIsLocal] = useState(true);
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [kwText, setKwText] = useState(SAMPLE);

  const { data: plan, loading, error, execute } = useApiCall<Plan>();
  const { ref: resultRef, trigger: scrollToResult } = useScrollIntoView();

  const run = useCallback(async () => {
    const snapshot = {
      ranking_query_count: Number(maturity),
      has_local_signals: isLocal,
    };
    const endpoint = mode === "discover" ? "/api/strategy/discover" : "/api/strategy";
    const payload =
      mode === "discover"
        ? { snapshot, business_description: description, location, language: lang }
        : { snapshot, keywords: parseKeywords(kwText) };

    const ok = await execute(() =>
      apiFetch<Plan>(endpoint, {
        method: "POST",
        body: JSON.stringify(payload),
      })
    );
    if (ok) scrollToResult();
  }, [mode, maturity, isLocal, description, location, lang, kwText, execute, scrollToResult]);

  return (
    <StrategyView
      mode={mode}
      maturity={maturity}
      isLocal={isLocal}
      description={description}
      location={location}
      kwText={kwText}
      plan={plan}
      error={error}
      loading={loading}
      resultRef={resultRef}
      onModeChange={setMode}
      onMaturityChange={setMaturity}
      onIsLocalChange={setIsLocal}
      onDescriptionChange={setDescription}
      onLocationChange={setLocation}
      onKwTextChange={setKwText}
      onResetSample={() => setKwText(SAMPLE)}
      onRun={run}
    />
  );
}
