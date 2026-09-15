"use client";

import { useEffect, useState } from "react";

import { hasTranslation, useT } from "@/lib/i18n";
import SenseRunPanel from "@/components/SenseRunPanel";
import type { GoogleStatus } from "@/lib/types/api";

type Field = {
  key: string;
  label: string;
  group: string;
  secret: boolean;
  description: string;
  placeholder: string;
  is_set: boolean;
  value: string;
};

type SettingsResponse = { demo_mode: boolean; fields: Field[] };

// Reasons the engine / login route attach to `?google=error&reason=…`.
const GOOGLE_ERROR_KEYS: Record<string, string> = {
  denied: "set.google.err.denied",
  state: "set.google.err.state",
  exchange: "set.google.err.exchange",
  not_configured: "set.google.err.not_configured",
  demo: "set.google.err.demo",
  unreachable: "set.google.err.unreachable",
};

export default function SettingsTool() {
  const { lang, t } = useT();
  const [demo, setDemo] = useState(false);
  const [fields, setFields] = useState<Field[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [verify, setVerify] = useState<{ valid: boolean; model?: string; reason?: string } | null>(
    null,
  );
  const [verifyingCms, setVerifyingCms] = useState(false);
  const [verifyCms, setVerifyCms] = useState<{ ok: boolean; detail?: string } | null>(null);
  // undefined = still checking, null = could not be checked.
  const [google, setGoogle] = useState<GoogleStatus | null | undefined>(undefined);
  const [googleNotice, setGoogleNotice] = useState<{ ok: boolean; key: string } | null>(null);
  const [connecting, setConnecting] = useState(false);

  async function loadGoogleStatus() {
    try {
      const res = await fetch("/api/auth/google/status");
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      setGoogle({ configured: Boolean(data?.configured), connected: Boolean(data?.connected) });
    } catch {
      setGoogle(null);
    }
  }

  function connectGoogle() {
    setConnecting(true);
    // A full navigation, not a fetch: the route redirects the browser to Google's
    // consent screen, and Google sends it back to this tab when done.
    window.location.assign("/api/auth/google/login");
  }

  async function load() {
    setLoading(true);
    try {
      const res = await fetch("/api/settings");
      const data: SettingsResponse = await res.json();
      setDemo(Boolean(data.demo_mode));
      setFields(data.fields ?? []);
    } catch {
      setStatus(t("common.unreachable"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    loadGoogleStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Outcome of a Google consent round-trip (`?google=connected|error&reason=…`).
  // Shown once, then removed from the URL so a reload does not repeat it.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const outcome = params.get("google");
    if (outcome === null) return;
    if (outcome === "connected") {
      setGoogleNotice({ ok: true, key: "set.google.done" });
    } else {
      const reason = params.get("reason") ?? "";
      setGoogleNotice({ ok: false, key: GOOGLE_ERROR_KEYS[reason] ?? "set.google.err.failed" });
    }
    window.history.replaceState(null, "", window.location.pathname);
  }, []);

  // Coming back with the browser's Back button restores this page from the
  // back/forward cache with the button still in its "opening" state; re-arm it.
  useEffect(() => {
    function onPageShow(e: PageTransitionEvent) {
      if (e.persisted) setConnecting(false);
    }
    window.addEventListener("pageshow", onPageShow);
    return () => window.removeEventListener("pageshow", onPageShow);
  }, []);

  async function save() {
    setStatus(t("set.saving"));
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: edits }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Save failed");
      setEdits({});
      setFields(data.fields ?? fields);
      setStatus(t("set.saved"));
      setVerify(null); // saved key changed → previous verdict is stale
      loadGoogleStatus(); // the OAuth client id/secret may have just been set
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function verifyKey() {
    setVerifying(true);
    setVerify(null);
    try {
      const res = await fetch("/api/settings/verify-llm", { method: "POST" });
      const data = await res.json();
      setVerify({ valid: Boolean(data?.valid), model: data?.model, reason: data?.reason });
    } catch {
      setVerify({ valid: false, reason: t("common.unreachable") });
    } finally {
      setVerifying(false);
    }
  }

  async function verifyCmsKey() {
    setVerifyingCms(true);
    setVerifyCms(null);
    try {
      const res = await fetch("/api/settings/verify-cms", { method: "POST" });
      const data = await res.json();
      setVerifyCms({ ok: Boolean(data?.ok), detail: data?.detail });
    } catch {
      setVerifyCms({ ok: false, detail: t("common.unreachable") });
    } finally {
      setVerifyingCms(false);
    }
  }

  // The engine describes fields in English, which English shows as-is. Other
  // languages use their own strings, falling back to the engine's text for any
  // field that has no translation yet.
  function localized(key: string, engineText: string) {
    return hasTranslation(lang, key) ? t(key) : engineText;
  }
  const groupKey = (group: string) => `set.group.${group.toLowerCase().replace(/\s+/g, "_")}`;

  if (loading) return <div className="panel">{t("set.loading")}</div>;

  const groups = Array.from(new Set(fields.map((f) => f.group)));
  const dirty = Object.keys(edits).length > 0;

  return (
    <div className="panel">
      {demo && (
        <div className="summary" style={{ borderLeftColor: "var(--warn)" }}>
          {t("set.demo")}
        </div>
      )}

      <div style={{ marginBottom: "1.5rem" }}>
        <h3
          style={{
            fontSize: "0.9rem",
            color: "var(--muted)",
            marginBottom: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}
        >
          {t("set.google.title")}
        </h3>
        {google === undefined && <p className="hint">{t("set.google.checking")}</p>}
        {google === null && (
          <p style={{ fontWeight: 600, color: "var(--warn)" }}>{t("set.google.unknown")}</p>
        )}
        {google && (
          <>
            <p
              style={{
                fontWeight: 600,
                color: google.connected
                  ? "var(--accent)"
                  : google.configured
                    ? "var(--text)"
                    : "var(--warn)",
              }}
            >
              {google.connected
                ? t("set.google.connected")
                : google.configured
                  ? t("set.google.notconnected")
                  : t("set.google.notconfigured")}
            </p>
            {demo ? (
              <p className="hint">{t("set.google.demo")}</p>
            ) : google.configured ? (
              <>
                <div style={{ marginTop: "0.5rem" }}>
                  <button
                    className={google.connected ? undefined : "primary"}
                    onClick={connectGoogle}
                    disabled={connecting || dirty}
                  >
                    {connecting
                      ? t("set.google.opening")
                      : google.connected
                        ? t("set.google.reconnect")
                        : t("set.google.connect")}
                  </button>
                </div>
                <p className="hint" style={{ marginTop: "0.5rem" }}>
                  {dirty ? t("set.google.savefirst") : t("set.google.hint")}
                </p>
              </>
            ) : (
              <p className="hint">{t("set.google.notconfigured.hint")}</p>
            )}
          </>
        )}
        {googleNotice && (
          <p
            style={{
              marginTop: "0.75rem",
              fontWeight: 600,
              color: googleNotice.ok ? "var(--accent)" : "var(--warn)",
            }}
          >
            {t(googleNotice.key)}
          </p>
        )}
      </div>

      <SenseRunPanel
        demo={demo}
        google={google}
        siteUrlSet={Boolean(fields.find((f) => f.key === "gsc_site_url")?.is_set)}
      />

      {groups.map((group) => (
        <div key={group} style={{ marginBottom: "1.5rem" }}>
          <h3
            style={{
              fontSize: "0.9rem",
              color: "var(--muted)",
              marginBottom: "0.75rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {localized(groupKey(group), group)}
          </h3>
          {fields
            .filter((f) => f.group === group)
            .map((f) => (
              <div className="field" key={f.key}>
                <label>
                  {localized(`set.field.${f.key}.label`, f.label)}
                  {f.secret && f.is_set && (
                    <span style={{ color: "var(--accent)", marginLeft: "0.5rem" }}>
                      {t("set.configured")}
                    </span>
                  )}
                </label>
                <input
                  type={f.secret ? "password" : "text"}
                  disabled={demo}
                  placeholder={
                    f.secret
                      ? f.is_set
                        ? t("set.keep")
                        : f.placeholder || t("set.notset")
                      : f.placeholder
                  }
                  defaultValue={f.secret ? "" : f.value}
                  onChange={(e) => setEdits((prev) => ({ ...prev, [f.key]: e.target.value }))}
                />
                <p className="hint">
                  {localized(`set.field.${f.key}.hint`, f.description)}
                </p>
              </div>
            ))}
        </div>
      ))}

      {!demo && (
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <button className="primary" onClick={save} disabled={!dirty}>
            {t("set.save")}
          </button>
          <button onClick={verifyKey} disabled={verifying}>
            {verifying ? t("set.verifying") : t("set.verify")}
          </button>
          <button onClick={verifyCmsKey} disabled={verifyingCms}>
            {verifyingCms ? t("set.noor.verifying") : t("set.noor.verify")}
          </button>
        </div>
      )}
      {!demo && (
        <p className="hint" style={{ marginTop: "0.5rem" }}>
          {t("set.verify.hint")}
        </p>
      )}
      {verify && (
        <p
          style={{
            marginTop: "0.75rem",
            fontWeight: 600,
            color: verify.valid ? "var(--accent)" : "var(--warn)",
          }}
        >
          {verify.valid
            ? `${t("set.verify.ok")}${verify.model ? ` (${verify.model})` : ""}`
            : `${t("set.verify.fail")}${verify.reason ? `: ${verify.reason}` : ""}`}
        </p>
      )}
      {!demo && (
        <p className="hint" style={{ marginTop: "0.5rem" }}>
          {t("set.noor.verify.hint")}
        </p>
      )}
      {verifyCms && (
        <p
          style={{
            marginTop: "0.75rem",
            fontWeight: 600,
            color: verifyCms.ok ? "var(--accent)" : "var(--warn)",
          }}
        >
          {verifyCms.ok
            ? `${t("set.noor.verify.ok")}${verifyCms.detail ? ` (${verifyCms.detail})` : ""}`
            : `${t("set.noor.verify.fail")}${verifyCms.detail ? `: ${verifyCms.detail}` : ""}`}
        </p>
      )}
      {status && (
        <p className="hint" style={{ marginTop: "0.75rem" }}>
          {status}
        </p>
      )}
    </div>
  );
}
