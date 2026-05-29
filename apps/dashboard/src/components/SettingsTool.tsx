"use client";

import { useEffect, useState } from "react";

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
      setStatus("Could not reach the engine.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function save() {
    setStatus("Saving…");
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
      setStatus("Saved ✓");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Save failed");
    }
  }

  if (loading) return <div className="panel">Loading settings…</div>;

  const groups = Array.from(new Set(fields.map((f) => f.group)));
  const dirty = Object.keys(edits).length > 0;

  return (
    <div className="panel">
      {demo && (
        <div className="summary" style={{ borderLeftColor: "var(--warn)" }}>
          🔒 This is a shared demo — settings are read-only. To use your own keys,
          self-host in one command (<code>docker compose up</code>) and configure
          everything from this same tab. No <code>.env</code> editing.
        </div>
      )}

      {groups.map((group) => (
        <div key={group} style={{ marginBottom: "1.5rem" }}>
          <h3 style={{ fontSize: "0.9rem", color: "var(--muted)", marginBottom: "0.75rem",
            textTransform: "uppercase", letterSpacing: "0.05em" }}>
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
                      ● configured
                    </span>
                  )}
                </label>
                <input
                  type={f.secret ? "password" : "text"}
                  disabled={demo}
                  placeholder={
                    f.secret
                      ? f.is_set
                        ? "•••••••• (leave blank to keep)"
                        : f.placeholder || "not set"
                      : f.placeholder
                  }
                  defaultValue={f.secret ? "" : f.value}
                  onChange={(e) =>
                    setEdits((prev) => ({ ...prev, [f.key]: e.target.value }))
                  }
                />
                <p className="hint">{f.description}</p>
              </div>
            ))}
        </div>
      ))}

      {!demo && (
        <button className="primary" onClick={save} disabled={!dirty}>
          Save settings
        </button>
      )}
      {status && <p className="hint" style={{ marginTop: "0.75rem" }}>{status}</p>}
    </div>
  );
}
