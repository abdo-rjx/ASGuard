import { useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Alert, Card, Empty, Field, RiskValue, StatusBadge, timeAgo } from "../components/ui";
import type { Application } from "../types";

export function Applications() {
  const { data, error, loading, refresh } = useApi<{ applications: Application[] }>(() => api.applications());
  const [editing, setEditing] = useState<Application | "new" | null>(null);

  return (
    <div>
      <p className="page-sub">
        Protected AI applications. ASGuard sits between each application and its upstream AI — it never accesses
        your databases, RAG stores or tools.
      </p>

      {error && <div style={{ marginBottom: 12 }}><Alert kind="error">{error}</Alert></div>}

      <Card title="Protected Applications" bodyClass="tight"
        actions={<button className="btn btn-sm btn-primary" onClick={() => setEditing("new")}>+ New Application</button>}>
        {loading && !data ? (
          <Empty><span className="spinning" /></Empty>
        ) : !data?.applications.length ? (
          <Empty>No applications configured.</Empty>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Application</th><th>Status</th><th>Upstream</th><th>Requests</th><th>Risk</th><th>Last Activity</th><th />
              </tr>
            </thead>
            <tbody>
              {data.applications.map((app) => (
                <tr key={app.id}>
                  <td>
                    <strong>{app.name}</strong>
                    <div style={{ fontSize: 11, color: "var(--faint)" }}>
                      {app.logging_mode === "content_preview" ? "preview logging" : "metadata only"}
                    </div>
                  </td>
                  <td><StatusBadge status={app.status} /></td>
                  <td className="mono" style={{ fontSize: 12 }}>{app.upstream_url}</td>
                  <td className="mono">{app.requests.toLocaleString()}</td>
                  <td><RiskValue score={Math.round(app.avg_risk)} /></td>
                  <td className="mono" style={{ fontSize: 12 }}>{timeAgo(app.last_activity_at)}</td>
                  <td>
                    <div className="row-actions">
                      <button className="btn btn-sm" onClick={() => setEditing(app)}>Configure</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {editing && (
        <AppForm
          app={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); refresh(); }}
        />
      )}
    </div>
  );
}

function AppForm({ app, onClose, onSaved }: { app: Application | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(app?.name ?? "");
  const [upstreamUrl, setUpstreamUrl] = useState(app?.upstream_url ?? "");
  const [upstreamApiKey, setUpstreamApiKey] = useState("");
  const [timeoutMs, setTimeoutMs] = useState(app?.timeout_ms ?? 60000);
  const [rateLimitRpm, setRateLimitRpm] = useState(app?.rate_limit_rpm ?? 120);
  const [loggingMode, setLoggingMode] = useState(app?.logging_mode ?? "metadata");
  const [isActive, setIsActive] = useState(app?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setSaving(true);
    setError(null);
    try {
      if (app) {
        await api.updateApplication(app.id, {
          name, upstream_url: upstreamUrl, timeout_ms: timeoutMs,
          rate_limit_rpm: rateLimitRpm, logging_mode: loggingMode, is_active: isActive,
          ...(upstreamApiKey ? { upstream_api_key: upstreamApiKey } : {}),
        });
      } else {
        await api.createApplication({
          name, upstream_url: upstreamUrl, timeout_ms: timeoutMs,
          rate_limit_rpm: rateLimitRpm, logging_mode: loggingMode,
          ...(upstreamApiKey ? { upstream_api_key: upstreamApiKey } : {}),
        });
      }
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <button className="drawer-close" onClick={onClose}>×</button>
        <h2 style={{ marginTop: 0 }}>{app ? `Configure: ${app.name}` : "New Application"}</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {error && <Alert kind="error">{error}</Alert>}
          {app && (
            <div className="field">
              <label>Client key — use it as the API key in your app</label>
              <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
                <input
                  readOnly
                  value={app.client_api_key}
                  onFocus={(e) => e.target.select()}
                  spellCheck={false}
                  style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}
                />
                <button
                  className="btn btn-sm"
                  type="button"
                  onClick={() => {
                    void navigator.clipboard.writeText(app.client_api_key);
                    alert(`Client key copied: ${app.client_api_key}`);
                  }}
                >
                  Copy
                </button>
              </div>
              <span className="hint">
                Set this as the <code className="inline">api_key</code> and ASGuard as the{" "}
                <code className="inline">base_url</code> in your OpenAI client — your app keeps its existing code.
              </span>
            </div>
          )}
          <Field label="Application name">
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label="Upstream AI URL" hint="OpenAI-compatible base URL, e.g. https://api.example.com/v1">
            <input value={upstreamUrl} onChange={(e) => setUpstreamUrl(e.target.value)} placeholder="https:// …/v1" />
          </Field>
          <Field label="Upstream API key" hint={app?.has_upstream_api_key ? "A key is configured (write-only). Leave blank to keep it." : "Sent to the upstream as a Bearer token."}>
            <input type="password" value={upstreamApiKey} onChange={(e) => setUpstreamApiKey(e.target.value)} autoComplete="new-password" />
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <Field label="Timeout (ms)">
              <input type="number" value={timeoutMs} onChange={(e) => setTimeoutMs(Number(e.target.value))} />
            </Field>
            <Field label="Rate limit (req/min)">
              <input type="number" value={rateLimitRpm} onChange={(e) => setRateLimitRpm(Number(e.target.value))} />
            </Field>
          </div>
          <Field label="Logging mode">
            <select value={loggingMode} onChange={(e) => setLoggingMode(e.target.value)}>
              <option value="metadata">Metadata only (recommended)</option>
              <option value="content_preview">Include content preview (explicit opt-in)</option>
            </select>
          </Field>
          <label className="toggle">
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Application active (accepts traffic)
          </label>
          <div className="row-actions">
            <button className="btn btn-primary" onClick={submit} disabled={saving || !name || !upstreamUrl}>
              {saving ? <span className="spinning" /> : "Save"}
            </button>
            <button className="btn" onClick={onClose}>Cancel</button>
          </div>
        </div>
      </div>
    </>
  );
}