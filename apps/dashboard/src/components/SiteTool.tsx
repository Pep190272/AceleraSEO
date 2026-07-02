"use client";

import React, { useCallback, useEffect, useState } from "react";

import { useT } from "@/lib/i18n";
import type {
  BlogStats,
  ImageStats,
  KeywordStats,
  PortfolioStats,
  SeoAudit,
  SeoPage,
  TextStats,
} from "@/lib/types/api";

// ── StatCard sub-component ────────────────────────────────────

function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div
      style={{
        padding: "0.75rem 1rem",
        background: "var(--surface, #f7f7f7)",
        borderRadius: "6px",
        minWidth: "120px",
      }}
    >
      <div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>{label}</div>
      {hint && <div style={{ fontSize: "0.75rem", color: "var(--warn, orange)", marginTop: "0.25rem" }}>{hint}</div>}
    </div>
  );
}

// ── EditForm sub-component ────────────────────────────────────

function EditForm({
  page,
  onSave,
  onCancel,
}: {
  page: SeoPage;
  onSave: (updated: SeoPage) => Promise<void>;
  onCancel: () => void;
}) {
  const { t } = useT();
  const [form, setForm] = useState<SeoPage>({ ...page });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function set(field: keyof SeoPage, value: string) {
    setForm((prev) => ({ ...prev, [field]: value || null }));
  }

  async function handleSave() {
    // Client-side guard: H1 is required and must have at least 3 non-whitespace chars.
    const h1NonWs = (form.h1 ?? "").replace(/[\s ]+/g, "");
    if (h1NonWs.length < 3) {
      setError(t("site.edit.h1.required"));
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave(form);
    } catch (e) {
      if (e instanceof Error) {
        setError(e.message);
      } else {
        setError(t("common.error"));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        padding: "1rem",
        border: "1px solid var(--border, #ddd)",
        borderRadius: "8px",
        marginTop: "0.5rem",
      }}
    >
      <h3 style={{ marginBottom: "0.75rem", fontSize: "1rem" }}>
        {t("site.edit.title")} <code style={{ fontSize: "0.85em" }}>{page.url}</code>
      </h3>

      <div className="field">
        <label>
          {t("site.edit.h1")} <span style={{ color: "var(--muted)", fontSize: "0.8em" }}>{t("site.edit.h1.hint")}</span>
        </label>
        <input
          value={form.h1 ?? ""}
          maxLength={60}
          onChange={(e) => set("h1", e.target.value)}
          placeholder={t("site.edit.h1.ph")}
        />
      </div>

      <div className="field">
        <label>
          {t("site.edit.h2")} <span style={{ color: "var(--muted)", fontSize: "0.8em" }}>{t("site.edit.h2.hint")}</span>
        </label>
        <input
          value={form.h2 ?? ""}
          maxLength={80}
          onChange={(e) => set("h2", e.target.value)}
          placeholder={t("site.edit.h2.ph")}
        />
      </div>

      <div className="field">
        <label>
          {t("site.edit.hero")} <span style={{ color: "var(--muted)", fontSize: "0.8em" }}>{t("site.edit.hero.hint")}</span>
        </label>
        <input
          value={form.hero_title ?? ""}
          maxLength={120}
          onChange={(e) => set("hero_title", e.target.value)}
          placeholder={t("site.edit.hero.ph")}
        />
      </div>

      <div className="field">
        <label>
          {t("site.edit.meta_title")} <span style={{ color: "var(--muted)", fontSize: "0.8em" }}>{t("site.edit.meta_title.hint")}</span>
        </label>
        <input
          value={form.meta_title ?? ""}
          maxLength={70}
          onChange={(e) => set("meta_title", e.target.value)}
          placeholder={t("site.edit.meta_title.ph")}
        />
      </div>

      <div className="field">
        <label>
          {t("site.edit.meta_desc")} <span style={{ color: "var(--muted)", fontSize: "0.8em" }}>{t("site.edit.meta_desc.hint")}</span>
        </label>
        <textarea
          value={form.meta_description ?? ""}
          maxLength={160}
          rows={3}
          onChange={(e) => set("meta_description", e.target.value)}
          placeholder={t("site.edit.meta_desc.ph")}
          style={{ width: "100%", resize: "vertical" }}
        />
      </div>

      {error && <div className="error">⚠ {error}</div>}

      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
        <button className="primary" onClick={handleSave} disabled={saving}>
          {saving ? t("site.edit.saving") : t("site.edit.save")}
        </button>
        <button onClick={onCancel} disabled={saving}>
          {t("site.edit.cancel")}
        </button>
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────

export default function SiteTool() {
  const { t } = useT();

  const [audit, setAudit] = useState<SeoAudit | null>(null);
  const [pages, setPages] = useState<SeoPage[]>([]);
  const [auditLoading, setAuditLoading] = useState(true);
  const [pagesLoading, setPagesLoading] = useState(true);
  const [auditError, setAuditError] = useState("");
  const [pagesError, setPagesError] = useState("");
  const [editingUrl, setEditingUrl] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState("");

  const loadAudit = useCallback(async () => {
    setAuditLoading(true);
    setAuditError("");
    try {
      const res = await fetch("/api/cms/audit");
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || t("common.error"));
      setAudit(data);
    } catch (e) {
      setAuditError(e instanceof Error ? e.message : t("common.error"));
    } finally {
      setAuditLoading(false);
    }
  }, [t]);

  const loadPages = useCallback(async () => {
    setPagesLoading(true);
    setPagesError("");
    try {
      const res = await fetch("/api/cms/pages");
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || t("common.error"));
      setPages(data.pages ?? []);
    } catch (e) {
      setPagesError(e instanceof Error ? e.message : t("common.error"));
    } finally {
      setPagesLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadAudit();
    loadPages();
  }, [loadAudit, loadPages]);

  function extractErrorDetail(data: unknown): string {
    if (!data || typeof data !== "object") return t("common.error");
    const d = data as Record<string, unknown>;
    // FastAPI validation errors send detail as an array of {msg, loc, type} objects.
    if (Array.isArray(d.detail)) {
      const msgs = (d.detail as Array<{ msg?: string }>)
        .map((item) => (typeof item?.msg === "string" ? item.msg : ""))
        .filter(Boolean);
      return msgs.length > 0 ? msgs.join("; ") : t("common.error");
    }
    if (typeof d.detail === "string") return d.detail;
    if (typeof d.error === "string") return d.error;
    return t("common.error");
  }

  async function handleSave(updated: SeoPage) {
    const res = await fetch("/api/cms/pages", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: updated.url,
        h1: updated.h1,
        h2: updated.h2 || null,
        hero_title: updated.hero_title || null,
        meta_title: updated.meta_title || null,
        meta_description: updated.meta_description || null,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(extractErrorDetail(data));
    setSaveSuccess(t("site.edit.saved").replace("{url}", updated.url));
    setEditingUrl(null);
    await loadPages();
    setTimeout(() => setSaveSuccess(""), 4000);
  }

  return (
    <div className="panel">
      <p className="lead">{t("site.lead")}</p>

      {/* ── SEO Audit ── */}
      <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>{t("site.audit.title")}</h2>

      {auditLoading && <p className="hint">{t("site.audit.loading")}</p>}
      {auditError && <div className="error">⚠ {auditError}</div>}

      {audit && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: "0.75rem",
            marginBottom: "1.5rem",
          }}
        >
          <StatCard
            label={t("site.audit.kw.active")}
            value={`${audit.keywords.active} / ${audit.keywords.total}`}
            hint={
              audit.keywords.urls_missing_meta.length > 0
                ? t("site.audit.kw.missing").replace(
                    "{n}",
                    String(audit.keywords.urls_missing_meta.length),
                  )
                : undefined
            }
          />
          <StatCard
            label={t("site.audit.textos.active")}
            value={`${audit.textos.active} / ${audit.textos.total}`}
          />
          <StatCard
            label={t("site.audit.images.missing_alt")}
            value={audit.images.portfolio_missing_alt}
          />
          <StatCard
            label={t("site.audit.blog.posts")}
            value={audit.blog.total_posts}
            hint={
              audit.blog.posts_without_meta > 0
                ? t("site.audit.blog.missing_meta").replace(
                    "{n}",
                    String(audit.blog.posts_without_meta),
                  )
                : undefined
            }
          />
          <StatCard label={t("site.audit.portfolio.published")} value={audit.portfolio.published} />
        </div>
      )}

      {/* ── Pages list ── */}
      <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>{t("site.pages.title")}</h2>

      {pagesLoading && <p className="hint">{t("site.pages.loading")}</p>}
      {pagesError && <div className="error">⚠ {pagesError}</div>}
      {saveSuccess && (
        <p style={{ color: "var(--accent)", fontWeight: 600 }}>{saveSuccess}</p>
      )}

      {!pagesLoading && !pagesError && pages.length === 0 && (
        <p className="hint">{t("site.pages.empty")}</p>
      )}

      {pages.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>{t("site.col.url")}</th>
              <th>{t("site.col.h1")}</th>
              <th>{t("site.col.meta_title")}</th>
              <th>{t("site.col.meta_desc")}</th>
              <th>{t("site.col.actions")}</th>
            </tr>
          </thead>
          <tbody>
            {pages.map((p) => (
              <React.Fragment key={p.url}>
                <tr>
                  <td>
                    <code style={{ fontSize: "0.85em" }}>{p.url}</code>
                  </td>
                  <td>{p.h1 || <span style={{ color: "var(--muted)" }}>—</span>}</td>
                  <td>
                    {p.meta_title ? (
                      <span title={p.meta_title}>
                        {p.meta_title.length > 35
                          ? p.meta_title.slice(0, 35) + "…"
                          : p.meta_title}
                      </span>
                    ) : (
                      <span style={{ color: "var(--muted)" }}>—</span>
                    )}
                  </td>
                  <td>
                    {p.meta_description ? (
                      <span title={p.meta_description}>
                        {p.meta_description.length > 45
                          ? p.meta_description.slice(0, 45) + "…"
                          : p.meta_description}
                      </span>
                    ) : (
                      <span style={{ color: "var(--muted)" }}>—</span>
                    )}
                  </td>
                  <td>
                    <button
                      className="link-btn"
                      onClick={() =>
                        setEditingUrl((prev) => (prev === p.url ? null : p.url))
                      }
                      type="button"
                    >
                      {editingUrl === p.url ? t("site.edit.cancel") : t("site.edit.btn")}
                    </button>
                  </td>
                </tr>
                {editingUrl === p.url && (
                  <tr key={`${p.url}-edit`}>
                    <td colSpan={5} style={{ padding: "0.5rem 0 1rem 0" }}>
                      <EditForm
                        page={p}
                        onSave={handleSave}
                        onCancel={() => setEditingUrl(null)}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}

      <p className="hint" style={{ marginTop: "1rem" }}>
        {t("site.pages.hint")}
      </p>
    </div>
  );
}
