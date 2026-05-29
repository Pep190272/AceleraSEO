"use client";

import { useT } from "@/lib/i18n";

// ES / EN switch in the header.
export default function LangToggle() {
  const { lang, setLang } = useT();
  return (
    <div className="lang-toggle">
      <button
        className={lang === "es" ? "on" : ""}
        onClick={() => setLang("es")}
        type="button"
      >
        ES
      </button>
      <span className="sep">/</span>
      <button
        className={lang === "en" ? "on" : ""}
        onClick={() => setLang("en")}
        type="button"
      >
        EN
      </button>
    </div>
  );
}
