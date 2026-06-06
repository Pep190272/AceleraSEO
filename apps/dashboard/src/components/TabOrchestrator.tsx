"use client";

import { useRef, useState } from "react";

import EngineStatus from "@/components/EngineStatus";
import LangToggle from "@/components/LangToggle";
import TabButton from "@/components/TabButton";
import { useT } from "@/lib/i18n";
import { TAB_CONFIG, type Tab } from "@/lib/tab-config";

export default function TabOrchestrator() {
  const { t } = useT();
  const [activeTab, setActiveTab] = useState<Tab>("strategy");

  // One ref per tab button so we can move focus on keyboard navigation.
  const tabRefs = useRef<Array<HTMLButtonElement | null>>(
    Array(TAB_CONFIG.length).fill(null),
  );

  const activeEntry = TAB_CONFIG.find((entry) => entry.id === activeTab);
  const ActivePanel = activeEntry?.component ?? null;

  /** Activate the tab at `index` and move focus to its button. */
  function activateAt(index: number) {
    setActiveTab(TAB_CONFIG[index].id);
    tabRefs.current[index]?.focus();
  }

  /** WAI-ARIA automatic-activation keyboard navigation for a tablist. */
  function handleKeyDown(e: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) {
    const last = TAB_CONFIG.length - 1;

    switch (e.key) {
      case "ArrowRight": {
        e.preventDefault();
        activateAt(currentIndex === last ? 0 : currentIndex + 1);
        break;
      }
      case "ArrowLeft": {
        e.preventDefault();
        activateAt(currentIndex === 0 ? last : currentIndex - 1);
        break;
      }
      case "Home": {
        e.preventDefault();
        activateAt(0);
        break;
      }
      case "End": {
        e.preventDefault();
        activateAt(last);
        break;
      }
    }
  }

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

      <div className="tabs" role="tablist" aria-label="Dashboard sections">
        {TAB_CONFIG.map((entry, index) => (
          <TabButton
            key={entry.id}
            id={entry.id}
            label={t(entry.labelKey)}
            isActive={activeTab === entry.id}
            onClick={() => setActiveTab(entry.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            ref={(el) => {
              tabRefs.current[index] = el;
            }}
          />
        ))}
      </div>

      {ActivePanel && (
        <div
          role="tabpanel"
          id={`panel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
          tabIndex={0}
        >
          <ActivePanel />
        </div>
      )}

      <footer>
        {t("footer.oss")}{" "}
        <a href="https://github.com/Pep190272/AceleraSEO" target="_blank" rel="noreferrer">
          github.com/Pep190272/AceleraSEO
        </a>
      </footer>
    </>
  );
}
