import { api } from "../services/api";
import { usePolling } from "../hooks/useApi";
import { Card, DecisionBadge, Empty, StatCard, timeAgo } from "../components/ui";
import type { Metrics, SecurityEvent } from "../types";
import { Donut } from "../components/charts";

const CATEGORY_LABELS: Record<string, string> = {
  secret: "Secrets",
  pii: "PII",
  financial: "Financial",
  confidential: "Confidential",
};

export function OutputSecurity() {
  const { data: metrics } = usePolling<Metrics>(() => api.metrics(24), 5000);
  const { data: events } = usePolling<{ events: SecurityEvent[] }>(
    () => api.events({ limit: 50 }),
    5000,
  );

  const counts = metrics?.threats_by_category ?? {};
  const outputEvents = (events?.events ?? []).filter((e) => e.direction === "output" || (e.stages?.length ?? 0) > 4);
  const sanitized = outputEvents.filter(
    (e) => e.decision === "SANITIZE" || e.stages?.some((s) => s.status === "SANITIZED"),
  ).length;
  const blocked = outputEvents.filter((e) => e.decision === "BLOCK" && e.error_code === "output_blocked").length;

  const donutSegments = [
    { label: "API Keys", value: counts.secret ?? 0, color: "var(--block)" },
    { label: "PII (phone/email)", value: counts.pii ?? 0, color: "var(--info)" },
    { label: "Financial", value: counts.financial ?? 0, color: "var(--sanitize)" },
    { label: "Confidential", value: counts.confidential ?? 0, color: "var(--review)" },
  ];

  return (
    <div>
      <p className="page-sub">
        AI output is inspected for secrets, PII and restricted data before it reaches the user.
      </p>

      <div className="grid metrics">
        <StatCard label="Responses Analyzed" value={metrics?.requests ?? 0} />
        <StatCard label="Sensitive Detections" value={metrics?.threats_detected ?? 0} dotColor="var(--review)" />
        <StatCard label="Secrets Detected" value={counts.secret ?? 0} dotColor="var(--block)" />
        <StatCard label="PII Detected" value={counts.pii ?? 0} dotColor="var(--info)" />
        <StatCard label="Sanitized Responses" value={sanitized} dotColor="var(--sanitize)" />
        <StatCard label="Blocked Responses" value={blocked} dotColor="var(--block)" />
      </div>

      <div className="section-gap" />
      <div className="grid two-thirds">
        <Card title="Detection Categories (24h)" bodyClass="">
          <div className="card-body">
            <Donut
              segments={donutSegments}
              centerLabel="detections"
              centerValue={(metrics?.threats_detected ?? 0).toLocaleString()}
            />
          </div>
        </Card>
        <Card title="Output Guard Pipeline">
          <div className="flow">
            {[
              ["Parse", "extract assistant content"],
              ["Detect", "secrets · PII · financial · confidential"],
              ["Score", "output risk engine"],
              ["Policy", "REDACT / SANITIZE / BLOCK"],
              ["Sanitize", "deterministic span removal"],
              ["Verify", "re-scan → fail closed if residue found"],
            ].map(([name, detail]) => (
              <div className="flow-stage" key={name}>
                <span className="flow-node OK" />
                <span className="flow-stage-name">{name}</span>
                <span style={{ fontSize: 11, color: "var(--faint)" }}>{detail}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="section-gap" />
      <Card title="Recent Output Decisions" bodyClass="tight">
        {outputEvents.length === 0 ? (
          <Empty>No output traffic yet.</Empty>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Time</th><th>Detection</th><th>Risk</th><th>Decision</th><th>Effect</th></tr>
            </thead>
            <tbody>
              {outputEvents.slice(0, 20).map((e) => {
                const detectedLabels = (e.threat_types ?? []).map((t) => CATEGORY_LABELS[t] ?? t);
                const sanitizeStage = e.stages?.find((s) => s.status === "SANITIZED");
                return (
                  <tr key={e.id}>
                    <td className="mono">{timeAgo(e.created_at)}</td>
                    <td>{detectedLabels.length ? detectedLabels.join(", ") : "—"}</td>
                    <td><span className="risk" style={{ color: e.risk_score >= 70 ? "var(--block)" : "var(--muted)" }}>{e.risk_score}</span></td>
                    <td><DecisionBadge decision={e.decision} /></td>
                    <td style={{ color: "var(--faint)", fontSize: 12 }}>
                      {sanitizeStage ? `sanitized: ${sanitizeStage.detail}` : e.error_code ?? "delivered"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}