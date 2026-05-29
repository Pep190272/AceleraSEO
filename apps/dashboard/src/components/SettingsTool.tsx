"use client";

import { useEffect, useState } from "react";

import { useT } from "@/lib/i18n";

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

export default function SettingsTool() {
  const { t } = useT();
  const [demo, setDemo] = useState(false);
  const [fields, setFields] = useState<Field[]>([]);
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    setStatus(t("set.saving"));
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(edits),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || data?.error || "Save failed");
      setEdits({});
      setFields(data.fields ?? fields);
      setStatus(t("set.saved"));
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Save failed");
    }
  }

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
            {group}
          </h3>
          {fields
            .filter((f) => f.group === group)
            .map((f) => (
              <div className="field" key={f.key}>
                <label>
                  {f.label}
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
                <p className="hint">{f.description}</p>
              </div>
            ))}
        </div>
      ))}

      {!demo && (
        <button className="primary" onClick={save} disabled={!dirty}>
          {t("set.save")}
        </button>
      )}
      {status && (
        <p className="hint" style={{ marginTop: "0.75rem" }}>
          {status}
        </p>
      )}
    </div>
  );
}
