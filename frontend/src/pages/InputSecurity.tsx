import { api } from "../services/api";
import { usePolling } from "../hooks/useApi";
import { Card, DecisionBadge, Empty, StatCard, timeAgo } from "../components/ui";
import type { Metrics, SecurityEvent } from "../types";
import { HBarChart } from "../components/charts";

const CATEGORY_LABELS: Record<string, string> = {
  prompt_injection: "Prompt Injection",
  jailbreak: "Jailbreak",
  system_prompt_extraction: "System Prompt Extraction",
  obfuscation: "Obfuscation",
  suspicious_intent: "Suspicious Intent",
};

export function InputSecurity() {
  const { data: metrics } = usePolling<Metrics>(() => api.metrics(24), 5000);
  const { data: events } = usePolling<{ events: SecurityEvent[] }>(
    () => api.events({ direction: "input", limit: 50 }),
    5000,
  );

  const counts = metrics?.threats_by_category ?? {};
  const totalThreats = Object.values(counts).reduce((a, b) => a + b, 0);
  const inputEvents = (events?.events ?? []).filter((e) => e.direction === "input");
  const blocked = inputEvents.filter((e) => e.decision === "BLOCK").length;
  const analyzed = metrics?.requests ?? 0;
  const falsePosThreats = inputEvents.filter(
    (e) => (e.decision === "REVIEW" || e.decision === "ALLOW") && e.threat_types.length > 0,
  ).length;

  return (
    <div>
      <p className="page-sub">
        Every request to your existing AI is normalized, inspected and scored before it is forwarded.
      </p>

      <div className="grid metrics">
        <StatCard label="Requests Analyzed" value={analyzed} />
        <StatCard label="Prompt Injections" value={counts.prompt_injection ?? 0} dotColor="var(--block)" />
        <StatCard label="Jailbreaks" value={counts.jailbreak ?? 0} dotColor="var(--block)" />
        <StatCard label="Blocked Requests" value={blocked} dotColor="var(--block)" />
        <StatCard label="False Positive Rate" value={analyzed ? `${((falsePosThreats / Math.max(1, analyzed)) * 100).toFixed(2)}%` : "—"} />
        <StatCard label="Avg Input Latency" value={metrics ? `${metrics.avg_latency_ms}ms` : "—"} />
      </div>

      <div className="section-gap" />
      <div className="grid half">
        <Card title="Input Guard Pipeline">
          <div className="flow">
            {[
              ["Normalize", "NFKC fold · homoglyph · leet · invisible chars"],
              ["Detect", "5 deterministic detectors (rules + patterns)"],
              ["Analyze", "intent analysis"],
              ["Score", "noisy-OR risk engine → 0..100"],
              ["Policy", "deterministic enforcement layer — final authority"],
            ].map(([name, detail]) => (
              <div className="flow-stage" key={name}>
                <span className="flow-node OK" />
                <span className="flow-stage-name">{name}</span>
                <span style={{ fontSize: 11, color: "var(--faint)" }}>{detail}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Detection Breakdown (24h)" bodyClass="">
          <div className="card-body">
            {totalThreats === 0 ? (
              <Empty>No input threats detected in this window.</Empty>
            ) : (
              <HBarChart
                entries={Object.entries(counts)
                  .filter(([k]) => k in CATEGORY_LABELS)
                  .sort((a, b) => b[1] - a[1])
                  .map(([k, v]) => ({ label: CATEGORY_LABELS[k] ?? k, value: v }))}
              />
            )}
          </div>
        </Card>
      </div>

      <div className="section-gap" />
      <Card title="Recent Input Decisions" bodyClass="tight">
        {inputEvents.length === 0 ? (
          <Empty>No input traffic yet.</Empty>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Time</th><th>Threat</th><th>Risk</th><th>Decision</th></tr>
            </thead>
            <tbody>
              {inputEvents.slice(0, 20).map((e) => (
                <tr key={e.id}>
                  <td className="mono">{timeAgo(e.created_at)}</td>
                  <td>{e.threat_types.length ? e.threat_types.map((t) => CATEGORY_LABELS[t] ?? t).join(", ") : "—"}</td>
                  <td><span className="risk risk-critical" style={{ color: e.risk_score >= 70 ? "var(--block)" : "var(--muted)" }}>{e.risk_score}</span></td>
                  <td><DecisionBadge decision={e.decision} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}