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
  set: Record<string, string>;
  setFields: Record<string, string>;
  common: Record<string, string>;
};

const NAMESPACED: Record<Lang, NamespacedDict> = {
  es: {
    nav: {
      "nav.strategy": "Estrategia",
      "nav.audit": "Auditoría técnica",
      "nav.settings": "Ajustes",
      "nav.competitors": "Competidores",
    },
    engine: {
      "engine.online": "motor en línea",
      "engine.offline": "motor desconectado",
      "engine.checking": "comprobando motor…",
    },
    hero: {
      "hero.title": "El experto, no otro panel de datos.",
      "hero.subtitle":
        "SEO autónomo de código abierto. Detecta tu posicionamiento real, decide la estrategia ganable para tu negocio, actúa y aprende. Pruébalo abajo — sin registro, sin claves API.",
    },
    footer: {
      "footer.oss": "Código abierto (MIT) ·",
    },
    strat: {
      "strat.lead":
        "Cuéntale al motor cómo es tu sitio y descubre qué palabras clave realmente vale la pena perseguir para tu situación.",
      "strat.mode.discover": "Descubrir palabras de mi nicho",
      "strat.mode.paste": "Ya tengo mis palabras",
      "strat.q1": "1 · ¿Qué tan consolidado está tu sitio?",
      "strat.q2": "2 · ¿Es un negocio local?",
      "strat.mat.new": "Nuevo — casi no posiciona aún",
      "strat.mat.growing": "En crecimiento — posiciona para algunos términos",
      "strat.mat.established": "Consolidado — posiciona para muchos",
      "strat.local.yes": "Sí — atiende una ciudad/zona",
      "strat.local.no": "No — online / a nivel nacional",
      "strat.describe.label": "3 · Describe tu negocio o nicho",
      "strat.describe.ph":
        "Ej: Fontanería de urgencias en Barcelona, reparaciones de fugas y calderas, atención 24h en el barrio de Gràcia.",
      "strat.location.label": "Ubicación (opcional, mejora lo local)",
      "strat.location.ph": "Barcelona, España",
      "strat.paste.label": "3 · Palabras clave que estás considerando",
      "strat.paste.hint": "una por línea: término, búsquedas mensuales, dificultad 0-100, intención",
      "strat.reset": "↺ Restablecer ejemplo",
      "strat.run.discover": "Descubrir mis palabras ganables →",
      "strat.run.paste": "Muéstrame qué vale la pena →",
      "strat.thinking": "Pensando…",
      "strat.needkey":
        "El descubrimiento necesita una clave de IA. Esta demo compartida funciona sin claves — usa el modo «Ya tengo mis palabras», o instala tu propia copia y agrega tu clave en Ajustes.",
    },
    res: {
      "res.title": "Aquí está tu plan",
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
      "res.verdict.skip": "Sáltala por ahora",
      "res.verdict.hint":
        "El veredicto = qué tan ganable es una palabra para TU autoridad, balanceando volumen de búsqueda contra dificultad. Mayor puntaje = mejor apuesta.",
      "res.actions.title": "Haz esto, en orden",
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
        "Ingresa un dominio y descubre quiénes son sus principales competidores orgánicos y para qué palabras clave ranquean.",
      "comp.domain.label": "Dominio a analizar",
      "comp.domain.ph": "ejemplo.com",
      "comp.location.label": "Ubicación (opcional)",
      "comp.location.ph": "España",
      "comp.run": "Analizar competidores →",
      "comp.analyzing": "Analizando…",
      "comp.error.nodomain": "Ingresa un dominio para analizar.",
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
    set: {
      "set.loading": "Cargando ajustes…",
      "set.demo":
        "🔒 Esta es una demo compartida — los ajustes son de solo lectura. Para usar tus propias claves, instala tu copia en un comando (docker compose up) y configura todo desde esta misma pestaña. Sin editar archivos.",
      "set.configured": "● configurado",
      "set.save": "Guardar ajustes",
      "set.saving": "Guardando…",
      "set.saved": "Guardado ✓",
      "set.keep": "•••••••• (deja vacío para mantener)",
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
      "set.google.title": "Conexión con Google",
      "set.google.checking": "Comprobando la conexión con Google…",
      "set.google.unknown":
        "No se pudo comprobar la conexión con Google: el motor no responde.",
      "set.google.connected": "● Conectado — el motor puede leer Search Console y Analytics",
      "set.google.notconnected": "○ Sin conectar",
      "set.google.notconfigured": "Sin configurar — faltan el ID y el secreto del cliente OAuth",
      "set.google.notconfigured.hint":
        "Pega el ID y el secreto del cliente OAuth en la sección Google de abajo, guarda, y podrás conectar tu cuenta.",
      "set.google.connect": "Conectar Google",
      "set.google.reconnect": "Volver a conectar Google",
      "set.google.opening": "Abriendo Google…",
      "set.google.hint":
        "Abre la pantalla de permisos de Google. Solo lectura de Search Console y Analytics; al terminar vuelves a esta pestaña.",
      "set.google.savefirst": "Guarda tus cambios antes de conectar.",
      "set.google.demo": "Conectar una cuenta de Google está desactivado en la demo compartida.",
      "set.google.done":
        "✓ Google conectado. El motor ya puede leer tus datos de Search Console y Analytics.",
      "set.google.err.denied": "✗ Cancelaste la conexión con Google — no se cambió nada.",
      "set.google.err.state":
        "✗ El enlace de inicio de sesión venció o ya se usó. Prueba conectar de nuevo.",
      "set.google.err.exchange":
        "✗ Google no aceptó el inicio de sesión. Revisa el ID y el secreto del cliente OAuth y la URI de redirección, y prueba de nuevo.",
      "set.google.err.not_configured":
        "✗ Google OAuth todavía no está configurado — agrega primero el ID y el secreto del cliente.",
      "set.google.err.demo": "✗ Conectar Google está desactivado en la demo compartida.",
      "set.google.err.unreachable": "✗ No se pudo contactar al motor para iniciar la conexión.",
      "set.google.err.failed": "✗ La conexión con Google falló. Prueba de nuevo.",
      "set.sense.title": "Recolección de datos",
      "set.sense.needs_google":
        "Configura el ID y el secreto del cliente OAuth de Google arriba para poder recolectar datos.",
      "set.sense.needs_connection": "Conecta tu cuenta de Google arriba antes de recolectar datos.",
      "set.sense.needs_site_url":
        "Falta la URL del sitio en Search Console. Configúrala en la sección Google de abajo.",
      "set.sense.run": "Ejecutar recolección",
      "set.sense.running": "Recolectando… puede tardar un rato en sitios grandes.",
      "set.sense.hint":
        "Trae las últimas posiciones de Search Console (y las conversiones de Analytics, si está configurado) y las guarda.",
      "set.sense.demo": "Ejecutar una recolección está desactivado en la demo compartida.",
      "set.sense.done": "✓ Recolección terminada.",
      "set.sense.rankings_fetched": "posiciones traídas",
      "set.sense.rankings_new": "filas nuevas",
      "set.sense.conversions": "páginas con conversiones",
      "set.sense.no_ga4":
        "No se recolectaron conversiones: falta el ID de propiedad de GA4 en Ajustes.",
    },
    // Spanish settings field labels and hints, keyed by the engine's field key and
    // group. The engine's English text is the source; English shows it unchanged.
    setFields: {
      "set.group.google": "Google",
      "set.group.ai_strategist": "Estratega IA",
      "set.group.market_data": "Datos de mercado",
      "set.group.indexing": "Indexación",
      "set.group.safety": "Seguridad",
      "set.group.noor_cms": "CMS Noor",
      "set.field.gsc_site_url.label": "URL del sitio en Search Console",
      "set.field.gsc_site_url.hint":
        "Por ejemplo sc-domain:ejemplo.com — la propiedad de la que se leen tus posiciones.",
      "set.field.ga4_property_id.label": "ID de propiedad de GA4",
      "set.field.ga4_property_id.hint": "ID numérico de tu propiedad de GA4, para las conversiones.",
      "set.field.google_oauth_client_id.label": "ID de cliente OAuth",
      "set.field.google_oauth_client_id.hint":
        "Lo obtienes en Google Cloud Console (APIs de Search Console y de Analytics Data).",
      "set.field.google_oauth_client_secret.label": "Secreto de cliente OAuth",
      "set.field.google_oauth_client_secret.hint": "Lo obtienes en Google Cloud Console.",
      "set.field.anthropic_api_key.label": "Clave API de Anthropic",
      "set.field.anthropic_api_key.hint":
        "Opcional — activa la explicación de la estrategia redactada por IA. Sin ella el motor funciona igual.",
      "set.field.anthropic_model.label": "Modelo de Anthropic",
      "set.field.anthropic_model.hint": "ID del modelo que redacta la explicación de la estrategia.",
      "set.field.dataforseo_login.label": "Usuario de DataForSEO",
      "set.field.dataforseo_login.hint":
        "Opcional — volumen y dificultad de palabras clave, con tu propia cuenta.",
      "set.field.dataforseo_password.label": "Contraseña de DataForSEO",
      "set.field.dataforseo_password.hint": "Opcional — va junto con el usuario de arriba.",
      "set.field.indexnow_key.label": "Clave de IndexNow",
      "set.field.indexnow_key.hint": "Opcional — indexación inmediata en Bing y Yandex (no en Google).",
      "set.field.indexnow_key_location.label": "URL de la clave de IndexNow",
      "set.field.indexnow_key_location.hint":
        "URL pública donde está publicado tu archivo de clave de IndexNow.",
      "set.field.autonomy_mode.label": "Modo de autonomía",
      "set.field.autonomy_mode.hint":
        "none = solo propone (lo más seguro, por defecto) · limited = limitado · full = total.",
      "set.field.max_auto_actions_per_day.label": "Máximo de acciones automáticas por día",
      "set.field.max_auto_actions_per_day.hint": "Tope estricto cuando la autonomía no es 'none'.",
      "set.field.noor_base_url.label": "URL base de Noor",
      "set.field.noor_base_url.hint":
        "URL base del sitio Noor que vas a gestionar, por ejemplo https://example.com.",
      "set.field.noor_api_key.label": "Clave API de Noor",
      "set.field.noor_api_key.hint": "Clave X-API-Key para autenticarse en la API SEO de Noor.",
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
      "set.google.title": "Google connection",
      "set.google.checking": "Checking the Google connection…",
      "set.google.unknown": "Could not check the Google connection: the engine is not responding.",
      "set.google.connected": "● Connected — the engine can read Search Console and Analytics",
      "set.google.notconnected": "○ Not connected",
      "set.google.notconfigured": "Not configured — needs the OAuth client ID and secret",
      "set.google.notconfigured.hint":
        "Paste the OAuth client ID and secret in the Google section below, save, and you can connect your account.",
      "set.google.connect": "Connect Google",
      "set.google.reconnect": "Reconnect Google",
      "set.google.opening": "Opening Google…",
      "set.google.hint":
        "Opens Google's consent screen. Read-only access to Search Console and Analytics; you come back to this tab when done.",
      "set.google.savefirst": "Save your changes before connecting.",
      "set.google.demo": "Connecting a Google account is disabled in the shared demo.",
      "set.google.done":
        "✓ Google connected. The engine can now read your Search Console and Analytics data.",
      "set.google.err.denied": "✗ You cancelled the Google connection — nothing was changed.",
      "set.google.err.state":
        "✗ The sign-in link expired or was already used. Try connecting again.",
      "set.google.err.exchange":
        "✗ Google did not accept the sign-in. Check the OAuth client ID, secret and redirect URI, then try again.",
      "set.google.err.not_configured":
        "✗ Google OAuth is not configured yet — add the client ID and secret first.",
      "set.google.err.demo": "✗ Connecting Google is disabled in the shared demo.",
      "set.google.err.unreachable": "✗ Could not reach the engine to start the connection.",
      "set.google.err.failed": "✗ The Google connection failed. Try again.",
      "set.sense.title": "Data collection",
      "set.sense.needs_google": "Configure the Google OAuth client ID and secret above to collect data.",
      "set.sense.needs_connection": "Connect your Google account above before collecting data.",
      "set.sense.needs_site_url":
        "The Search Console site URL is missing. Set it in the Google section below.",
      "set.sense.run": "Run collection",
      "set.sense.running": "Collecting… this can take a while on large sites.",
      "set.sense.hint":
        "Pulls the latest rankings from Search Console (and conversions from Analytics, if configured) and saves them.",
      "set.sense.demo": "Running a collection is disabled in the shared demo.",
      "set.sense.done": "✓ Collection finished.",
      "set.sense.rankings_fetched": "rankings fetched",
      "set.sense.rankings_new": "new rows",
      "set.sense.conversions": "pages with conversions",
      "set.sense.no_ga4": "No conversions were collected: the GA4 property ID is missing in Settings.",
    },
    // Empty on purpose: English shows the engine's own field text (see SettingsTool).
    setFields: {},
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

// True only when `lang` itself defines `key` — no English fallback and no dev
// warning, for callers that have their own fallback text.
export function hasTranslation(lang: Lang, key: string): boolean {
  return Object.prototype.hasOwnProperty.call(STRINGS[lang], key);
}

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
