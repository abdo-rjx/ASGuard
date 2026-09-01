import { useEffect, useState, useSyncExternalStore } from "react";
import { api, desktopConfig, isDesktop, probeBackend } from "../services/api";
import { connection } from "../services/connection";
import { useApi } from "../hooks/useApi";
import { Alert, Card } from "../components/ui";
import type { SettingsDoc } from "../types";

/** Desktop-only card: point the app at any ASGuard instance, or run offline. */
function ConnectionCard() {
  const status = useSyncExternalStore(connection.subscribe, connection.get);
  const [url, setUrl] = useState(desktopConfig.backendUrl);
  const [demo, setDemo] = useState(desktopConfig.forceDemo);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function saveAndTest() {
    setTesting(true);
    setResult(null);
    desktopConfig.setBackendUrl(url);
    const next = await probeBackend();
    setResult(next === "live" ? "Connected — live backend data." : "Backend unreachable — running on the offline demo simulator.");
    setTesting(false);
  }

  const statusColor = status === "live" ? "var(--patina)" : status === "demo" ? "var(--gold)" : "var(--faint)";
  const statusLabel = status === "live" ? "Connected to backend" : status === "demo" ? "Offline demo simulator" : "Searching…";

  return (
    <Card title="Desktop Connection">
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="field">
          <label>
            ASGuard backend URL
            <span style={{ marginLeft: 10, color: statusColor, fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              ● {statusLabel}
            </span>
          </label>
          <input
            value={url}
            placeholder="http://127.0.0.1:8000"
            onChange={(e) => setUrl(e.target.value)}
            spellCheck={false}
          />
          <span className="hint">
            Point this at any running ASGuard instance — local (<code className="inline">uvicorn asguard.api.main:app</code>),
            Docker, or a remote deployment. The app stays fully usable without one via the built-in demo data.
          </span>
        </div>
        <label className="toggle">
          <input
            type="checkbox"
            checked={demo}
            onChange={(e) => {
              desktopConfig.setForceDemo(e.target.checked);
              setDemo(e.target.checked);
              void probeBackend();
            }}
          />
          Always use offline demo data (ignore backend)
        </label>
        <div className="row-actions">
          <button className="btn btn-primary" onClick={saveAndTest} disabled={testing}>
            {testing ? <span className="spinning" /> : "Save & Test Connection"}
          </button>
          {result && <span style={{ fontSize: 12.5, color: "var(--muted)", alignSelf: "center" }}>{result}</span>}
        </div>
      </div>
    </Card>
  );
}

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

      {isDesktop && (
        <>
          <ConnectionCard />
          <div className="section-gap" />
        </>
      )}

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