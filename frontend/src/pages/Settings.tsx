import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Alert, Card } from "../components/ui";
import type { SettingsDoc } from "../types";

export function Settings() {
  const { data, error, loading, refresh } = useApi<SettingsDoc>(() => api.settings());
  const [form, setForm] = useState<SettingsDoc | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "ok"; text: string } | null>(null);

  useEffect(() => {
    if (data && !form) setForm(data);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  async function save() {
    if (!form) return;
    setSaving(true);
    setMessage(null);
    try {
      await api.updateSettings(form as unknown as Record<string, unknown>);
      setMessage({ kind: "ok", text: "Settings saved." });
      refresh();
    } catch (e) {
      setMessage({ kind: "error", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  }

  if (loading && !data) {
    return (
      <Card>
        <div className="card-body"><span className="spinning" /> Loading settings…</div>
      </Card>
    );
  }
  if (error && !data) {
    return <Alert kind="error">{error}</Alert>;
  }
  if (!form) return null;

  const set = (section: keyof SettingsDoc, key: string, value: unknown) => {
    setForm((prev) => {
      if (!prev) return prev;
      const next = JSON.parse(JSON.stringify(prev)) as SettingsDoc;
      (next[section] as Record<string, unknown>)[key] = value;
      return next;
    });
  };

  return (
    <div>
      <p className="page-sub">
        Runtime security configuration. Changes are validated server-side and applied to the live engine
        without a restart. All values use safe defaults.
      </p>

      {message && <div style={{ marginBottom: 12 }}><Alert kind={message.kind}>{message.text}</Alert></div>}

      <div className="grid half">
        <Card title="Security Thresholds">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <NumberField
              label="Block threshold" value={form.security_thresholds.block_threshold} min={0} max={100}
              onChange={(v) => set("security_thresholds", "block_threshold", v)}
              hint="Requests/responses at or above this risk are BLOCKED."
            />
            <NumberField
              label="Review threshold" value={form.security_thresholds.review_threshold} min={0} max={100}
              onChange={(v) => set("security_thresholds", "review_threshold", v)}
              hint="Requests at or above this risk are flagged for REVIEW (must be ≤ block threshold)."
            />
          </div>
        </Card>

        <Card title="Detection & Policy">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="field">
              <label>Detector failure mode</label>
              <select
                value={form.detection.detector_failure_mode}
                onChange={(e) => set("detection", "detector_failure_mode", e.target.value)}
              >
                <option value="fail_closed">fail_closed (fail safe — default)</option>
                <option value="fail_open">fail_open (allow when a detector crashes)</option>
              </select>
              <span className="hint">Critical security failures fail safe by default.</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="section-gap" />

      <div className="grid half">
        <Card title="Logging">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <div className="field">
              <label>Log level</label>
              <select value={form.logging.log_level} onChange={(e) => set("logging", "log_level", e.target.value)}>
                {["DEBUG", "INFO", "WARNING", "ERROR"].map((l) => <option key={l}>{l}</option>)}
              </select>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={form.logging.log_security_events}
                onChange={(e) => set("logging", "log_security_events", e.target.checked)}
              />
              Persist security events to the audit store
            </label>
          </div>
        </Card>

        <Card title="Privacy & Retention">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <NumberField
              label="Retention (days)" value={form.privacy.retention_days} min={1} max={3650}
              onChange={(v) => set("privacy", "retention_days", v)}
            />
            <label className="toggle">
              <input type="checkbox" checked={form.privacy.store_raw_content} disabled />
              Store raw prompts/responses
              <span style={{ fontSize: 11, color: "var(--block)" }}>— locked false: ASGuard never stores raw content</span>
            </label>
          </div>
        </Card>
      </div>

      <div className="section-gap" />

      <div className="grid half">
        <Card title="Upstream">
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <NumberField
              label="Upstream timeout (seconds)" value={form.upstream.timeout_seconds} min={1} max={600}
              onChange={(v) => set("upstream", "timeout_seconds", v)}
            />
          </div>
        </Card>
      </div>
      <div className="section-gap" />
      <button className="btn btn-primary" onClick={save} disabled={saving || loading}>
        {saving ? <span className="spinning" /> : "Save Settings"}
      </button>
    </div>
  );
}

function NumberField({ label, value, min, max, onChange, hint }: {
  label: string; value: number; min: number; max: number;
  onChange: (v: number) => void; hint?: string;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      {hint && <span className="hint">{hint}</span>}
    </div>
  );
}