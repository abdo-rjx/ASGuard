import { useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Alert, Card, Empty } from "../components/ui";
import type { Policy } from "../types";

const PRETTY: Record<string, string> = {
  prompt_injection: "Prompt Injection",
  jailbreak: "Jailbreak",
  system_prompt_extraction: "System Prompt Extraction",
  obfuscation: "Obfuscation",
  suspicious_intent: "Suspicious Intent",
  secret: "API Key / Secret",
  pii: "PII (phone, email)",
  financial: "Financial Data",
  confidential: "Confidential Data",
};

export function Policies() {
  const { data, error, loading, refresh } = useApi<{ policies: Policy[] }>(() => api.policies());
  const [saving, setSaving] = useState<string | null>(null);
  const [message, setMessage] = useState<{ kind: "error" | "ok"; text: string } | null>(null);

  async function save(policy: Policy) {
    setSaving(policy.id);
    setMessage(null);
    try {
      await api.updatePolicy(policy.id, {
        action: policy.action,
        threshold: policy.threshold,
        enabled: policy.enabled,
        reason: "updated from dashboard",
      });
      setMessage({ kind: "ok", text: `Policy ${PRETTY[policy.category] ?? policy.category} saved.` });
      refresh();
    } catch (e) {
      setMessage({ kind: "error", text: (e as Error).message });
    } finally {
      setSaving(null);
    }
  }

  const inputPolicies = (data?.policies ?? []).filter((p) => p.direction === "input");
  const outputPolicies = (data?.policies ?? []).filter((p) => p.direction === "output");

  return (
    <div>
      <p className="page-sub">
        Deterministic rules evaluated by the policy engine for every transaction. The policy engine is the final
        enforcement authority — detector signals alone never decide.
      </p>

      {message && (
        <div style={{ marginBottom: 12 }}>
          <Alert kind={message.kind}>{message.text}</Alert>
        </div>
      )}
      {error && (
        <div style={{ marginBottom: 12 }}>
          <Alert kind="error">{error}</Alert>
        </div>
      )}

      <PolicySection title="Input Policies" policies={inputPolicies} direction="input" saving={saving} onSave={save} />
      <div className="section-gap" />
      <PolicySection title="Output Policies" policies={outputPolicies} direction="output" saving={saving} onSave={save} />

      {loading && !data && <Empty><span className="spinning" /></Empty>}
    </div>
  );
}

function PolicySection({ title, policies, direction, saving, onSave }: {
  title: string;
  policies: Policy[];
  direction: "input" | "output";
  saving: string | null;
  onSave: (p: Policy) => void;
}) {
  return (
    <Card title={title} bodyClass="tight">
      {policies.length === 0 ? (
        <Empty>No {direction} policies configured.</Empty>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Category</th><th>Action</th><th>Threshold</th><th>Enabled</th><th style={{ textAlign: "right" }}>Save</th>
            </tr>
          </thead>
          <tbody>
            {policies.map((p) => (
              <PolicyRow key={p.id} policy={p} direction={direction} saving={saving === p.id} onSave={onSave} />
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

function PolicyRow({ policy, direction, saving, onSave }: {
  policy: Policy;
  direction: "input" | "output";
  saving: boolean;
  onSave: (p: Policy) => void;
}) {
  const [action, setAction] = useState(policy.action);
  const [threshold, setThreshold] = useState(policy.threshold);
  const [enabled, setEnabled] = useState(policy.enabled);
  const dirty = action !== policy.action || threshold !== policy.threshold || enabled !== policy.enabled;

  return (
    <tr>
      <td>{PRETTY[policy.category] ?? policy.category}</td>
      <td>
        <select value={action} onChange={(e) => setAction(e.target.value)} style={{ width: 140 }}>
          {policy.allowed_actions.map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
      </td>
      <td>
        <input
          type="number"
          min={0}
          max={100}
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          style={{ width: 90 }}
        />
        <span style={{ color: "var(--faint)", fontSize: 11, marginLeft: 6 }}>
          {direction === "input" ? "risk ≥" : "risk ≥"}
        </span>
      </td>
      <td>
        <label className="toggle">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
          {enabled ? "on" : "off"}
        </label>
      </td>
      <td style={{ textAlign: "right" }}>
        <button className="btn btn-sm" disabled={!dirty || saving} onClick={() => onSave({ ...policy, action, threshold, enabled })}>
          {saving ? <span className="spinning" /> : "Save"}
        </button>
      </td>
    </tr>
  );
}