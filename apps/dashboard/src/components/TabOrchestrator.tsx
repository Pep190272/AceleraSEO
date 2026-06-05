"use client";

import { useState } from "react";

import EngineStatus from "@/components/EngineStatus";
import LangToggle from "@/components/LangToggle";
import TabButton from "@/components/TabButton";
import { useT } from "@/lib/i18n";
import { TAB_CONFIG, type Tab } from "@/lib/tab-config";

export default function TabOrchestrator() {
  const { t } = useT();
  const [activeTab, setActiveTab] = useState<Tab>("strategy");

  const activeEntry = TAB_CONFIG.find((entry) => entry.id === activeTab);
  const ActivePanel = activeEntry?.component ?? null;

  return (
    <>
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
        {TAB_CONFIG.map((entry) => (
          <TabButton
            key={entry.id}
            label={t(entry.labelKey)}
            isActive={activeTab === entry.id}
            onClick={() => setActiveTab(entry.id)}
          />
        ))}
      </div>

      {ActivePanel && <ActivePanel />}

      <footer>
        {t("footer.oss")}{" "}
        <a href="https://github.com/Pep190272/AceleraSEO" target="_blank" rel="noreferrer">
          github.com/Pep190272/AceleraSEO
        </a>
      </footer>
    </>
  );
}
