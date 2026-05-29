"use client";

import { useState } from "react";

import AuditTool from "@/components/AuditTool";
import EngineStatus from "@/components/EngineStatus";
import SettingsTool from "@/components/SettingsTool";
import StrategyTool from "@/components/StrategyTool";

type Tab = "strategy" | "audit" | "settings";

export default function Home() {
  const [tab, setTab] = useState<Tab>("strategy");

  return (
    <div className="container">
      <header className="site">
        <div className="brand">
          Acelera<span>SEO</span>
        </div>
        <EngineStatus />
      </header>

      <div className="hero">
        <h1>The expert, not another data dashboard.</h1>
        <p>
          Open-source autonomous SEO. It senses your real rankings, decides the winnable strategy
          for your business, acts, and learns. Try the brain below — no signup, no API keys.
        </p>
      </div>

      <div className="tabs">
        <button
          className={`tab ${tab === "strategy" ? "active" : ""}`}
          onClick={() => setTab("strategy")}
        >
          Strategy engine
        </button>
        <button
          className={`tab ${tab === "audit" ? "active" : ""}`}
          onClick={() => setTab("audit")}
        >
          Technical audit
        </button>
        <button
          className={`tab ${tab === "settings" ? "active" : ""}`}
          onClick={() => setTab("settings")}
        >
          Settings
        </button>
      </div>

      {tab === "strategy" && <StrategyTool />}
      {tab === "audit" && <AuditTool />}
      {tab === "settings" && <SettingsTool />}

      <footer>
        Open source (MIT) ·{" "}
        <a href="https://github.com/Pep190272/AceleraSEO" target="_blank" rel="noreferrer">
          github.com/Pep190272/AceleraSEO
        </a>
      </footer>
    </div>
  );
}
