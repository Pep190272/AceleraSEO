"use client";

import { useState } from "react";

import AuditTool from "@/components/AuditTool";
import EngineStatus from "@/components/EngineStatus";
import LangToggle from "@/components/LangToggle";
import SettingsTool from "@/components/SettingsTool";
import StrategyTool from "@/components/StrategyTool";
import { useT } from "@/lib/i18n";

type Tab = "strategy" | "audit" | "settings";

export default function Home() {
  const { t } = useT();
  const [tab, setTab] = useState<Tab>("strategy");

  return (
    <div className="container">
      <header className="site">
        <div className="brand">
          Acelera<span>SEO</span>
        </div>
        <div className="header-right">
          <LangToggle />
          <EngineStatus />
        </div>
      </header>

      <div className="hero">
        <h1>{t("hero.title")}</h1>
        <p>{t("hero.subtitle")}</p>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === "strategy" ? "active" : ""}`} onClick={() => setTab("strategy")}>
          {t("nav.strategy")}
        </button>
        <button className={`tab ${tab === "audit" ? "active" : ""}`} onClick={() => setTab("audit")}>
          {t("nav.audit")}
        </button>
        <button className={`tab ${tab === "settings" ? "active" : ""}`} onClick={() => setTab("settings")}>
          {t("nav.settings")}
        </button>
      </div>

      {tab === "strategy" && <StrategyTool />}
      {tab === "audit" && <AuditTool />}
      {tab === "settings" && <SettingsTool />}

      <footer>
        {t("footer.oss")}{" "}
        <a href="https://github.com/Pep190272/AceleraSEO" target="_blank" rel="noreferrer">
          github.com/Pep190272/AceleraSEO
        </a>
      </footer>
    </div>
  );
}
