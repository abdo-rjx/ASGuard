import { useState } from "react";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Alert, Card, Empty, RiskValue, timeAgo } from "../components/ui";
import type { TestRunSummary } from "../types";

const CATEGORY_LABELS: Record<string, string> = {
  prompt_injection: "Prompt Injection",
  jailbreak: "Jailbreak",
  system_prompt_extraction: "System Prompt Extraction",
  obfuscation: "Obfuscation",
  suspicious_intent: "Suspicious Intent",
  secret: "Secret Leakage",
  pii: "PII Leakage",
  financial: "Financial Data",
  confidential: "Confidential Data",
  benign: "False-positive guard",
};

export function Testing() {
  const [running, setRunning] = useState(false);
  const [latest, setLatest] = useState<TestRunSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { data: history, refresh } = useApi<{ runs: TestRunSummary[] }>(() => api.testResults());

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const result = await api.runTests();
      const summary: TestRunSummary = {
        id: result.run_id,
        started_at: new Date().toISOString(),
        total: result.total,
        passed: result.passed,
        failed: result.failed,
        results: result.results,
      };
      setLatest(summary);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  const results = latest?.results ?? [];

  return (
    <div>
      <p className="page-sub">
        Run the built-in security corpus against the live detection and policy engine. Every case executes real
        backend logic — no simulated results.
      </p>

      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14 }}>
        <button className="btn btn-primary" onClick={run} disabled={running}>
          {running ? <><span className="spinning" /> Running suite…</> : "▶ Run Full Security Suite"}
        </button>
        {latest && (
          <span className="badge badge-neutral">
            {latest.total} cases · {latest.passed} passed · {latest.failed} failed
          </span>
        )}
      </div>

      {error && <div style={{ marginBottom: 12 }}><Alert kind="error">{error}</Alert></div>}

      {results.length > 0 && (
        <Card title="Latest Run Results" bodyClass="tight">
          <table className="table">
            <thead>
              <tr>
                <th>Test</th><th>Category</th><th>Expected</th><th>Actual</th><th>Result</th><th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.id}</td>
                  <td>{CATEGORY_LABELS[r.category] ?? r.category}</td>
                  <td><span className="badge badge-neutral">{r.expected_decision}</span></td>
                  <td><span className={`badge badge-${r.passed ? "PASS" : "FAIL"}`} style={{ background: "none" }}>
                    {r.actual_decision}
                  </span></td>
                  <td><span className={`badge badge-${r.passed ? "PASS" : "FAIL"}`}>{r.passed ? "PASS" : "FAIL"}</span></td>
                  <td><RiskValue score={r.risk_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {!latest && results.length === 0 && (
        <Card bodyClass="">
          <div className="card-body">
            <Empty>
              <span className="spinning" style={{ marginRight: 8 }} />
              No run yet. Click "Run Full Security Suite" to execute the YAML corpus against the live engine.
            </Empty>
          </div>
        </Card>
      )}

      <div className="section-gap" />
      <Card title="Recent Runs" bodyClass="tight">
        {!history?.runs.length ? (
          <Empty>No previous runs.</Empty>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Run</th><th>Started</th><th>Total</th><th>Passed</th><th>Failed</th></tr>
            </thead>
            <tbody>
              {history.runs.map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.id.slice(0, 12)}…</td>
                  <td className="mono">{timeAgo(r.started_at)}</td>
                  <td>{r.total}</td>
                  <td style={{ color: "var(--allow)" }}>{r.passed}</td>
                  <td style={{ color: r.failed ? "var(--block)" : "var(--faint)" }}>{r.failed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}