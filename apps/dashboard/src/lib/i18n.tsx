"use client";

// Lightweight i18n: a translations dict + a provider + a useT() hook.
// Default language is Spanish; the header toggle persists the choice.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type Lang = "es" | "en";

// ---------------------------------------------------------------------------
// Internal namespaced structure — organized by feature for maintainability.
// Callers NEVER import this; they use t("some.key") via the hook.
// The flat lookup dict (STRINGS) is derived below by flattening these objects,
// so every t() call site continues to work byte-for-byte identical.
// ---------------------------------------------------------------------------

type NamespacedDict = {
  nav: Record<string, string>;
  engine: Record<string, string>;
  hero: Record<string, string>;
  footer: Record<string, string>;
  strat: Record<string, string>;
  res: Record<string, string>;
  audit: Record<string, string>;
  comp: Record<string, string>;
  site: Record<string, string>;
  set: Record<string, string>;
  common: Record<string, string>;
};

const NAMESPACED: Record<Lang, NamespacedDict> = {
  es: {
    nav: {
      "nav.strategy": "Estrategia",
      "nav.audit": "Auditoría técnica",
      "nav.settings": "Ajustes",
      "nav.competitors": "Competidores",
      "nav.site": "Mi sitio",
    },
    engine: {
      "engine.online": "motor en línea",
      "engine.offline": "motor desconectado",
      "engine.checking": "comprobando motor…",
    },
    hero: {
      "hero.title": "El experto, no otro panel de datos.",
      "hero.subtitle":
        "SEO autónomo de código abierto. Detecta tu posicionamiento real, decide la estrategia ganable para tu negocio, actúa y aprende. Probalo abajo — sin registro, sin claves API.",
    },
    footer: {
      "footer.oss": "Código abierto (MIT) ·",
    },
    strat: {
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
    },
    res: {
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
    },
    audit: {
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
    },
    comp: {
      "comp.lead":
        "Ingresá un dominio y descubrí quiénes son sus principales competidores orgánicos y para qué palabras clave ranquean.",
      "comp.domain.label": "Dominio a analizar",
      "comp.domain.ph": "ejemplo.com",
      "comp.location.label": "Ubicación (opcional)",
      "comp.location.ph": "España",
      "comp.run": "Analizar competidores →",
      "comp.analyzing": "Analizando…",
      "comp.error.nodomain": "Ingresá un dominio para analizar.",
      "comp.res.title": "Competidores encontrados",
      "comp.res.empty": "No se encontraron competidores para este dominio.",
      "comp.res.hint":
        "Fuente: DataForSEO Labs. Se muestran hasta 5 competidores con hasta 10 palabras clave cada uno.",
      "comp.col.domain": "Dominio competidor",
      "comp.col.common": "Palabras comunes",
      "comp.col.avgpos": "Pos. media",
      "comp.col.traffic": "Tráfico estimado",
      "comp.col.keywords": "Palabras clave",
      "comp.kw.show": "Ver {n} palabras",
      "comp.kw.hide": "Ocultar palabras",
      "comp.kw.none": "Sin datos",
      "comp.kw.col.term": "Término",
      "comp.kw.col.pos": "Posición",
      "comp.kw.col.vol": "Volumen",
    },
    site: {
      "site.lead":
        "Revisá el estado SEO de tu sitio Noor, listá sus páginas y editá sus meta etiquetas y encabezados directamente desde acá.",
      "site.audit.title": "Salud SEO del sitio",
      "site.audit.loading": "Cargando auditoría…",
      "site.audit.kw.active": "Keywords activas",
      "site.audit.kw.missing": "{n} páginas sin meta",
      "site.audit.textos.active": "Textos activos",
      "site.audit.images.missing_alt": "Imágenes sin alt",
      "site.audit.blog.posts": "Posts de blog",
      "site.audit.blog.missing_meta": "{n} sin meta",
      "site.audit.portfolio.published": "Proyectos publicados",
      "site.pages.title": "Páginas SEO",
      "site.pages.loading": "Cargando páginas…",
      "site.pages.empty": "No se encontraron páginas SEO configuradas.",
      "site.pages.hint":
        "Fuente: API de Noor. Editar una página reemplaza todos sus campos — completá los que ya tenía para no perderlos.",
      "site.col.url": "URL",
      "site.col.h1": "H1 (keyword)",
      "site.col.meta_title": "Meta título",
      "site.col.meta_desc": "Meta descripción",
      "site.col.actions": "Acciones",
      "site.edit.btn": "Editar",
      "site.edit.title": "Editando",
      "site.edit.h1": "H1 (keyword principal)",
      "site.edit.h1.hint": "3–60 caracteres, sin < ni >",
      "site.edit.h1.ph": "Ej: Construcción y reformas en Madrid",
      "site.edit.h2": "H2 (keyword secundaria)",
      "site.edit.h2.hint": "hasta 80 caracteres",
      "site.edit.h2.ph": "Ej: Reformas integrales de pisos",
      "site.edit.hero": "Hero title",
      "site.edit.hero.hint": "hasta 120 caracteres",
      "site.edit.hero.ph": "Ej: Construimos tu hogar ideal",
      "site.edit.meta_title": "Meta título",
      "site.edit.meta_title.hint": "hasta 70 caracteres",
      "site.edit.meta_title.ph": "Ej: Construcciones Noor | Reformas en Madrid",
      "site.edit.meta_desc": "Meta descripción",
      "site.edit.meta_desc.hint": "hasta 160 caracteres",
      "site.edit.meta_desc.ph":
        "Ej: Empresa de construcción y reformas en Madrid. Presupuesto gratis, atención personalizada.",
      "site.edit.h1.required": "H1 es obligatorio (mínimo 3 caracteres sin espacios).",
      "site.edit.save": "Guardar cambios",
      "site.edit.saving": "Guardando…",
      "site.edit.saved": "✓ Guardado: {url}",
      "site.edit.cancel": "Cancelar",
    },
    set: {
      "set.loading": "Cargando ajustes…",
      "set.demo":
        "🔒 Esta es una demo compartida — los ajustes son de solo lectura. Para usar tus propias claves, instalá tu copia en un comando (docker compose up) y configurá todo desde esta misma pestaña. Sin editar archivos.",
      "set.configured": "● configurado",
      "set.save": "Guardar ajustes",
      "set.saving": "Guardando…",
      "set.saved": "Guardado ✓",
      "set.keep": "•••••••• (dejá vacío para mantener)",
      "set.notset": "sin configurar",
      "set.verify": "Probar conexión con la IA",
      "set.verifying": "Comprobando la clave…",
      "set.verify.ok": "✓ Clave válida",
      "set.verify.fail": "✗ Clave inválida",
      "set.verify.hint":
        "Comprueba que tu clave de IA esté activa y que el modelo configurado responda. No consume tokens.",
      "set.noor.verify": "Probar conexión con Noor",
      "set.noor.verifying": "Comprobando…",
      "set.noor.verify.ok": "✓ Conexión con Noor OK",
      "set.noor.verify.fail": "✗ No se pudo conectar con Noor",
      "set.noor.verify.hint": "Comprueba que la URL base y la clave API de Noor son correctas.",
    },
    common: {
      "common.error": "Error",
      "common.unreachable": "No se pudo contactar al motor.",
    },
  },
  en: {
    nav: {
      "nav.strategy": "Strategy",
      "nav.audit": "Technical audit",
      "nav.settings": "Settings",
      "nav.competitors": "Competitors",
      "nav.site": "My site",
    },
    engine: {
      "engine.online": "engine online",
      "engine.offline": "engine offline",
      "engine.checking": "checking engine…",
    },
    hero: {
      "hero.title": "The expert, not another data dashboard.",
      "hero.subtitle":
        "Open-source autonomous SEO. It senses your real rankings, decides the winnable strategy for your business, acts, and learns. Try it below — no signup, no API keys.",
    },
    footer: {
      "footer.oss": "Open source (MIT) ·",
    },
    strat: {
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
    },
    res: {
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
    },
    audit: {
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
    },
    comp: {
      "comp.lead":
        "Enter a domain and discover its top organic competitors along with the keywords they rank for.",
      "comp.domain.label": "Domain to analyze",
      "comp.domain.ph": "example.com",
      "comp.location.label": "Location (optional)",
      "comp.location.ph": "Spain",
      "comp.run": "Analyze competitors →",
      "comp.analyzing": "Analyzing…",
      "comp.error.nodomain": "Enter a domain to analyze.",
      "comp.res.title": "Competitors found",
      "comp.res.empty": "No competitors found for this domain.",
      "comp.res.hint":
        "Source: DataForSEO Labs. Shows up to 5 competitors with up to 10 keywords each.",
      "comp.col.domain": "Competitor domain",
      "comp.col.common": "Common keywords",
      "comp.col.avgpos": "Avg. position",
      "comp.col.traffic": "Est. traffic",
      "comp.col.keywords": "Keywords",
      "comp.kw.show": "Show {n} keywords",
      "comp.kw.hide": "Hide keywords",
      "comp.kw.none": "No data",
      "comp.kw.col.term": "Term",
      "comp.kw.col.pos": "Position",
      "comp.kw.col.vol": "Volume",
    },
    site: {
      "site.lead":
        "Review the SEO health of your Noor site, list its pages, and edit their meta tags and headings directly from here.",
      "site.audit.title": "Site SEO health",
      "site.audit.loading": "Loading audit…",
      "site.audit.kw.active": "Active keywords",
      "site.audit.kw.missing": "{n} pages missing meta",
      "site.audit.textos.active": "Active texts",
      "site.audit.images.missing_alt": "Images missing alt",
      "site.audit.blog.posts": "Blog posts",
      "site.audit.blog.missing_meta": "{n} without meta",
      "site.audit.portfolio.published": "Published projects",
      "site.pages.title": "SEO pages",
      "site.pages.loading": "Loading pages…",
      "site.pages.empty": "No SEO-configured pages found.",
      "site.pages.hint":
        "Source: Noor API. Editing a page replaces ALL its fields — fill in the ones already set to avoid clearing them.",
      "site.col.url": "URL",
      "site.col.h1": "H1 (keyword)",
      "site.col.meta_title": "Meta title",
      "site.col.meta_desc": "Meta description",
      "site.col.actions": "Actions",
      "site.edit.btn": "Edit",
      "site.edit.title": "Editing",
      "site.edit.h1": "H1 (main keyword)",
      "site.edit.h1.hint": "3–60 chars, no < or >",
      "site.edit.h1.ph": "e.g. Construction and renovations in Madrid",
      "site.edit.h2": "H2 (secondary keyword)",
      "site.edit.h2.hint": "up to 80 chars",
      "site.edit.h2.ph": "e.g. Full flat renovations",
      "site.edit.hero": "Hero title",
      "site.edit.hero.hint": "up to 120 chars",
      "site.edit.hero.ph": "e.g. We build your ideal home",
      "site.edit.meta_title": "Meta title",
      "site.edit.meta_title.hint": "up to 70 chars",
      "site.edit.meta_title.ph": "e.g. Noor Constructions | Renovations in Madrid",
      "site.edit.meta_desc": "Meta description",
      "site.edit.meta_desc.hint": "up to 160 chars",
      "site.edit.meta_desc.ph":
        "e.g. Construction and renovation company in Madrid. Free quote, personal service.",
      "site.edit.h1.required": "H1 is required (min 3 non-whitespace characters).",
      "site.edit.save": "Save changes",
      "site.edit.saving": "Saving…",
      "site.edit.saved": "✓ Saved: {url}",
      "site.edit.cancel": "Cancel",
    },
    set: {
      "set.loading": "Loading settings…",
      "set.demo":
        "🔒 This is a shared demo — settings are read-only. To use your own keys, self-host in one command (docker compose up) and configure everything from this same tab. No file editing.",
      "set.configured": "● configured",
      "set.save": "Save settings",
      "set.saving": "Saving…",
      "set.saved": "Saved ✓",
      "set.keep": "•••••••• (leave blank to keep)",
      "set.notset": "not set",
      "set.verify": "Test AI connection",
      "set.verifying": "Checking the key…",
      "set.verify.ok": "✓ Key valid",
      "set.verify.fail": "✗ Key invalid",
      "set.verify.hint":
        "Checks that your AI key is active and the configured model responds. Spends no tokens.",
      "set.noor.verify": "Test Noor connection",
      "set.noor.verifying": "Checking…",
      "set.noor.verify.ok": "✓ Connected to Noor",
      "set.noor.verify.fail": "✗ Could not connect to Noor",
      "set.noor.verify.hint": "Checks that the Noor base URL and API key are correct.",
    },
    common: {
      "common.error": "Error",
      "common.unreachable": "Could not reach the engine.",
    },
  },
};

// ---------------------------------------------------------------------------
// Flat lookup dict — built once at module load by merging all namespace buckets.
// Every t("some.key") call resolves against this, identical to before.
// ---------------------------------------------------------------------------

type Dict = Record<string, string>;

function flatten(namespaced: NamespacedDict): Dict {
  // Object.assign mutates the accumulator in one pass; spreading would copy every
  // key already merged on each bucket, making this O(n²) in the number of keys.
  return Object.values(namespaced).reduce<Dict>((acc, bucket) => {
    return Object.assign(acc, bucket);
  }, {});
}

const STRINGS: Record<Lang, Dict> = {
  es: flatten(NAMESPACED.es),
  en: flatten(NAMESPACED.en),
};

// ---------------------------------------------------------------------------
// TranslationKey — union of every known key derived from the Spanish dict
// (es is the canonical source; en must mirror it).
// The parameter type is `TranslationKey | (string & {})` so:
//   - IDEs autocomplete known keys
//   - Existing call sites passing arbitrary strings still compile
//   - We don't introduce a breaking build error; tightening is a later slice
// ---------------------------------------------------------------------------

export type TranslationKey = keyof typeof STRINGS.es;

// ---------------------------------------------------------------------------
// Provider + hook
// ---------------------------------------------------------------------------

type Ctx = {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (k: TranslationKey | (string & {})) => string;
};

const LangCtx = createContext<Ctx>({ lang: "es", setLang: () => {}, t: (k) => k as string });

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("es");

  useEffect(() => {
    // Narrow with a real check rather than asserting over `false | string | null`.
    const saved = typeof window === "undefined" ? null : localStorage.getItem("lang");
    if (saved === "es" || saved === "en") setLangState(saved);
  }, []);

  // Keep document.documentElement.lang in sync on the client.
  // The server renders html lang="es" (the documented default) to avoid a
  // hydration mismatch — we can't know localStorage at SSR time without
  // cookies or a server action. We intentionally accept this: the attribute
  // flips client-side on mount for non-default langs, which is invisible to
  // users and avoids the React hydration warning that would occur if the
  // server-rendered value differed from the initial React tree value.
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  // setLang closes over nothing that changes, so it is stable for the provider's
  // whole lifetime.
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem("lang", l);
  }, []);

  // t reads STRINGS, a module-level constant, so `lang` is its only dependency:
  // one stable identity per language rather than a new one per render.
  const t = useCallback(
    (k: TranslationKey | (string & {})): string => {
      const key = k as string;
      const value = STRINGS[lang][key] ?? STRINGS.en[key];
      if (value !== undefined) return value;
      // Warn in development so missing keys surface during authoring.
      // Guarded so the check is tree-shaken out of production bundles.
      if (process.env.NODE_ENV !== "production") {
        console.warn(`[i18n] Missing translation key: "${key}" (lang: ${lang})`);
      }
      return key;
    },
    [lang],
  );

  // Memoized: an object literal here would be a new value on every render, so every
  // consumer would re-render and every effect keyed on `t` would re-run — including
  // data fetches in tabs that have nothing to do with the language.
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <LangCtx.Provider value={value}>{children}</LangCtx.Provider>;
}

export function useT() {
  return useContext(LangCtx);
}
