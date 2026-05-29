"use client";

// Lightweight i18n: a translations dict + a provider + a useT() hook.
// Default language is Spanish; the header toggle persists the choice.
import { createContext, useContext, useEffect, useState } from "react";

export type Lang = "es" | "en";

type Dict = Record<string, string>;

const STRINGS: Record<Lang, Dict> = {
  es: {
    "nav.strategy": "Estrategia",
    "nav.audit": "Auditoría técnica",
    "nav.settings": "Ajustes",
    "engine.online": "motor en línea",
    "engine.offline": "motor desconectado",
    "engine.checking": "comprobando motor…",
    "hero.title": "El experto, no otro panel de datos.",
    "hero.subtitle":
      "SEO autónomo de código abierto. Detecta tu posicionamiento real, decide la estrategia ganable para tu negocio, actúa y aprende. Probalo abajo — sin registro, sin claves API.",
    "footer.oss": "Código abierto (MIT) ·",

    // Strategy — modes
    "strat.lead":
      "Contale al motor cómo es tu sitio y descubrí qué palabras clave realmente vale la pena perseguir para tu situación.",
    "strat.mode.discover": "Descubrir palabras de mi nicho",
    "strat.mode.paste": "Ya tengo mis palabras",
    "strat.q1": "1 · ¿Qué tan consolidado está tu sitio?",
    "strat.q2": "2 · ¿Es un negocio local?",
    "strat.mat.new": "Nuevo — casi no posiciona aún",
    "strat.mat.growing": "En crecimiento — posiciona para algunos términos",
    "strat.mat.established": "Consolidado — posiciona para muchos",
    "strat.local.yes": "Sí — atiende una ciudad/zona",
    "strat.local.no": "No — online / a nivel nacional",
    "strat.describe.label": "3 · Describí tu negocio o nicho",
    "strat.describe.ph":
      "Ej: Fontanería de urgencias en Barcelona, reparaciones de fugas y calderas, atención 24h en el barrio de Gràcia.",
    "strat.location.label": "Ubicación (opcional, mejora lo local)",
    "strat.location.ph": "Barcelona, España",
    "strat.paste.label": "3 · Palabras clave que estás considerando",
    "strat.paste.hint": "una por línea: término, búsquedas mensuales, dificultad 0-100, intención",
    "strat.reset": "↺ Restablecer ejemplo",
    "strat.run.discover": "Descubrir mis palabras ganables →",
    "strat.run.paste": "Mostrame qué vale la pena →",
    "strat.thinking": "Pensando…",
    "strat.needkey":
      "El descubrimiento necesita una clave de IA. Esta demo compartida funciona sin claves — usá el modo «Ya tengo mis palabras», o instalá tu propia copia y agregá tu clave en Ajustes.",

    // Strategy — results
    "res.title": "Acá está tu plan",
    "res.profile.a": "Tu sitio parece un negocio",
    "res.profile.b": "con autoridad",
    "res.profile.c":
      ". Eso significa que conviene perseguir palabras que puedas ganar ahora — no las más grandes.",
    "res.col.keyword": "Palabra clave",
    "res.col.verdict": "Veredicto",
    "res.col.score": "Puntaje",
    "res.verdict.best": "★ Mejor apuesta",
    "res.verdict.good": "Vale la pena",
    "res.verdict.hard": "Difícil por ahora",
    "res.verdict.skip": "Saltala por ahora",
    "res.verdict.hint":
      "El veredicto = qué tan ganable es una palabra para TU autoridad, balanceando volumen de búsqueda contra dificultad. Mayor puntaje = mejor apuesta.",
    "res.actions.title": "Hacé esto, en orden",
    "res.actions.fixfirst": "arreglar primero",

    // Audit
    "audit.label": "URL del sitio a auditar",
    "audit.run": "Ejecutar auditoría técnica",
    "audit.running": "Rastreando…",
    "audit.hint":
      "Rastrea el sitio (mismo dominio, hasta 25 páginas) y reporta problemas SEO por severidad.",
    "audit.pages": "páginas",
    "audit.critical": "críticos",
    "audit.warning": "advertencias",
    "audit.notice": "avisos",
    "audit.none": "No se encontraron problemas en las páginas rastreadas. ✓",
    "audit.col.sev": "Severidad",
    "audit.col.issue": "Problema",
    "audit.col.url": "URL",

    // Settings
    "set.loading": "Cargando ajustes…",
    "set.demo":
      "🔒 Esta es una demo compartida — los ajustes son de solo lectura. Para usar tus propias claves, instalá tu copia en un comando (docker compose up) y configurá todo desde esta misma pestaña. Sin editar archivos.",
    "set.configured": "● configurado",
    "set.save": "Guardar ajustes",
    "set.saving": "Guardando…",
    "set.saved": "Guardado ✓",
    "set.keep": "•••••••• (dejá vacío para mantener)",
    "set.notset": "sin configurar",
    "common.error": "Error",
    "common.unreachable": "No se pudo contactar al motor.",
  },
  en: {
    "nav.strategy": "Strategy",
    "nav.audit": "Technical audit",
    "nav.settings": "Settings",
    "engine.online": "engine online",
    "engine.offline": "engine offline",
    "engine.checking": "checking engine…",
    "hero.title": "The expert, not another data dashboard.",
    "hero.subtitle":
      "Open-source autonomous SEO. It senses your real rankings, decides the winnable strategy for your business, acts, and learns. Try it below — no signup, no API keys.",
    "footer.oss": "Open source (MIT) ·",

    "strat.lead":
      "Tell the engine about your site and discover which keywords are actually worth chasing for your situation.",
    "strat.mode.discover": "Discover keywords for my niche",
    "strat.mode.paste": "I already have my keywords",
    "strat.q1": "1 · How established is your site?",
    "strat.q2": "2 · Is it a local business?",
    "strat.mat.new": "Brand new — barely ranks yet",
    "strat.mat.growing": "Growing — ranks for some terms",
    "strat.mat.established": "Established — ranks for a lot",
    "strat.local.yes": "Yes — serves a city/area",
    "strat.local.no": "No — online / nationwide",
    "strat.describe.label": "3 · Describe your business or niche",
    "strat.describe.ph":
      "e.g. Emergency plumbing in Barcelona, leak and boiler repairs, 24h service in the Gràcia district.",
    "strat.location.label": "Location (optional, improves local results)",
    "strat.location.ph": "Barcelona, Spain",
    "strat.paste.label": "3 · Keywords you're considering",
    "strat.paste.hint": "one per line: term, monthly searches, difficulty 0-100, intent",
    "strat.reset": "↺ Reset example",
    "strat.run.discover": "Discover my winnable keywords →",
    "strat.run.paste": "Show me what's worth chasing →",
    "strat.thinking": "Thinking…",
    "strat.needkey":
      "Discovery needs an AI key. This shared demo runs keyless — use “I already have my keywords”, or self-host and add your key in Settings.",

    "res.title": "Here's your plan",
    "res.profile.a": "Your site looks like a",
    "res.profile.b": "business with",
    "res.profile.c":
      " authority. That means you should chase keywords you can win now — not the biggest ones.",
    "res.col.keyword": "Keyword",
    "res.col.verdict": "Verdict",
    "res.col.score": "Score",
    "res.verdict.best": "★ Best bet",
    "res.verdict.good": "Worth it",
    "res.verdict.hard": "Hard right now",
    "res.verdict.skip": "Skip for now",
    "res.verdict.hint":
      "Verdict = how winnable a keyword is for YOUR authority, balancing search volume against difficulty. Higher score = better bet.",
    "res.actions.title": "Do this, in order",
    "res.actions.fixfirst": "fix first",

    "audit.label": "Site URL to audit",
    "audit.run": "Run technical audit",
    "audit.running": "Crawling…",
    "audit.hint":
      "Crawls the site (same-host, up to 25 pages) and reports severity-tagged SEO issues.",
    "audit.pages": "pages",
    "audit.critical": "critical",
    "audit.warning": "warning",
    "audit.notice": "notice",
    "audit.none": "No issues found on the crawled pages. ✓",
    "audit.col.sev": "Severity",
    "audit.col.issue": "Issue",
    "audit.col.url": "URL",

    "set.loading": "Loading settings…",
    "set.demo":
      "🔒 This is a shared demo — settings are read-only. To use your own keys, self-host in one command (docker compose up) and configure everything from this same tab. No file editing.",
    "set.configured": "● configured",
    "set.save": "Save settings",
    "set.saving": "Saving…",
    "set.saved": "Saved ✓",
    "set.keep": "•••••••• (leave blank to keep)",
    "set.notset": "not set",
    "common.error": "Error",
    "common.unreachable": "Could not reach the engine.",
  },
};

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: string) => string };
const LangCtx = createContext<Ctx>({ lang: "es", setLang: () => {}, t: (k) => k });

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("es");

  useEffect(() => {
    const saved = (typeof window !== "undefined" && localStorage.getItem("lang")) as Lang | null;
    if (saved === "es" || saved === "en") setLangState(saved);
  }, []);

  function setLang(l: Lang) {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem("lang", l);
  }

  const t = (k: string) => STRINGS[lang][k] ?? STRINGS.en[k] ?? k;

  return <LangCtx.Provider value={{ lang, setLang, t }}>{children}</LangCtx.Provider>;
}

export function useT() {
  return useContext(LangCtx);
}
