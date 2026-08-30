import { Link } from "react-router-dom";
import { api } from "../services/api";
import { usePolling } from "../hooks/useApi";
import { Card, DecisionBadge, DirBadge, Empty, RiskValue, StatCard, clockTime } from "../components/ui";
import { Reveal } from "../components/motion";
import { StackedBarChart } from "../components/charts";
import { GuardDiagram } from "../components/PipelineFlow";

const POLL_MS = 5000;

export function Dashboard() {
  const { data: metrics } = usePolling(() => api.metrics(24), POLL_MS);
  const { data: series } = usePolling(() => api.timeseries(24), POLL_MS);

  return (
    <div>
      <p className="page-sub">
        Live security posture of the AI firewall — all metrics come from real proxied traffic (last 24h).
      </p>

      <div className="grid metrics">
        {[0, 1, 2, 3, 4, 5].map((slot) => {
          const cards = [
            <StatCard key="req" label="Requests" value={metrics?.requests ?? 0} />,
            <StatCard key="allow" label="Allowed" value={metrics?.allowed ?? 0} dotColor="var(--patina)" />,
            <StatCard key="block" label="Blocked" value={metrics?.blocked ?? 0} dotColor="var(--block)" />,
            <StatCard key="san" label="Sanitized" value={metrics?.sanitized ?? 0} dotColor="var(--gold)" />,
            <StatCard key="threat" label="Threats" value={metrics?.threats_detected ?? 0} dotColor="var(--review)" />,
            <StatCard key="risk" label="Avg Risk" value={metrics ? metrics.avg_risk : 0} decimals={1}
                      sub={metrics ? `avg latency ${metrics.avg_latency_ms}ms` : undefined} />,
          ];
          return <Reveal key={slot} i={slot}>{cards[slot]}</Reveal>;
        })}
      </div>

      <div className="section-gap" />

      <Reveal i={2}>
        <Card title="Bidirectional Protection">
          <GuardDiagram inputDecision="policy" outputDecision="policy" />
        </Card>
      </Reveal>

      <div className="section-gap" />

      <Reveal i={3}>
        <Card title="Traffic Over Time (24h)">
          {series ? <StackedBarChart data={series} /> : <Empty>Loading…</Empty>}
          <div style={{ display: "flex", gap: 16, marginTop: 10, fontSize: 12, color: "var(--muted)" }}>
            <span><span className="stat-dot" style={{ background: "var(--patina)", display: "inline-block", marginRight: 6 }} />Allowed</span>
            <span><span className="stat-dot" style={{ background: "var(--block)", display: "inline-block", marginRight: 6 }} />Blocked</span>
            <span><span className="stat-dot" style={{ background: "var(--gold)", display: "inline-block", marginRight: 6 }} />Sanitized</span>
            <span><span className="stat-dot" style={{ background: "var(--review)", display: "inline-block", marginRight: 6 }} />Review</span>
          </div>
        </Card>
      </Reveal>

      <div className="section-gap" />

      <Reveal i={4}>
        <Card
          title="Live Security Activity"
          actions={<Link to="/events" className="link" style={{ fontSize: 13 }}>All events →</Link>}
          bodyClass="tight"
        >
          {!metrics || metrics.recent_events.length === 0 ? (
            <Empty>No security events yet — proxy a request through <code className="inline">/v1/chat/completions</code>.</Empty>
          ) : (
            <table className="table anim-rows">
              <thead>
                <tr>
                  <th>Time</th><th>Direction</th><th>Threat</th><th>Risk</th><th>Decision</th><th>Application</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {metrics.recent_events.map((e, i) => (
                  <tr key={e.id} className="clickable" style={{ ["--i" as string]: i }}
                      onClick={() => (window.location.href = `/inspector/${e.id}`)}>
                    <td className="mono">{clockTime(e.created_at)}</td>
                    <td><DirBadge direction={e.direction} /></td>
                    <td>{e.threat_types.length ? e.threat_types.join(", ") : "—"}</td>
                    <td><RiskValue score={e.risk_score} /></td>
                    <td><DecisionBadge decision={e.decision} /></td>
                    <td>{e.application_name ?? "—"}</td>
                    <td className="mono" style={{ color: e.error_code ? "var(--block)" : "var(--muted)" }}>
                      {e.error_code ?? e.upstream_status}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </Reveal>
    </div>
  );
}
