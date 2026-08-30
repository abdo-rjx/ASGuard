import { useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import { useApi } from "../hooks/useApi";
import { Card, DecisionBadge, DirBadge, Empty, RiskValue, clockTime, timeAgo } from "../components/ui";
import type { SecurityEvent } from "../types";

type DirectionFilter = "" | "input" | "output";
type DecisionFilter = "" | "ALLOW" | "BLOCK" | "SANITIZE" | "REVIEW" | "ERROR";

export function Events() {
  const [direction, setDirection] = useState<DirectionFilter>("");
  const [decision, setDecision] = useState<DecisionFilter>("");
  const { data, error, loading, refresh } = useApi<{ total: number; events: SecurityEvent[] }>(
    () =>
      api.events({
        limit: 100,
        direction: direction || undefined,
        decision: decision || undefined,
      }),
    [direction, decision],
  );

  return (
    <div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14 }}>
        <FieldControl label="Direction">
          <select value={direction} onChange={(e) => setDirection(e.target.value as DirectionFilter)} style={{ width: 130 }}>
            <option value="">All</option>
            <option value="input">INPUT</option>
            <option value="output">OUTPUT</option>
          </select>
        </FieldControl>
        <FieldControl label="Decision">
          <select value={decision} onChange={(e) => setDecision(e.target.value as DecisionFilter)} style={{ width: 130 }}>
            <option value="">All</option>
            <option value="ALLOW">ALLOW</option>
            <option value="BLOCK">BLOCK</option>
            <option value="SANITIZE">SANITIZE</option>
            <option value="REVIEW">REVIEW</option>
            <option value="ERROR">ERROR</option>
          </select>
        </FieldControl>
        <button className="btn" onClick={refresh}>Refresh</button>
        {data && <span style={{ color: "var(--faint)", fontSize: 13 }}>{data.total} event(s)</span>}
      </div>

      <Card bodyClass="tight">
        {loading ? (
          <Empty><span className="spinning" /></Empty>
        ) : error ? (
          <Empty>{error}</Empty>
        ) : !data?.events.length ? (
          <Empty>No events match. Send traffic through <code className="inline">/v1/chat/completions</code>.</Empty>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Time</th><th>Direction</th><th>Threat</th><th>Risk</th><th>Decision</th><th>Application</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {data.events.map((e) => (
                <tr key={e.id} className="clickable">
                  <td className="mono">
                    {clockTime(e.created_at)}
                    <div style={{ color: "var(--faint)", fontSize: 11 }}>{timeAgo(e.created_at)}</div>
                  </td>
                  <td><DirBadge direction={e.direction} /></td>
                  <td>{e.threat_types.length ? e.threat_types.join(", ") : "—"}</td>
                  <td><RiskValue score={e.risk_score} /></td>
                  <td><Link to={`/inspector/${e.id}`} style={{ textDecoration: "none" }}><DecisionBadge decision={e.decision} /></Link></td>
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
    </div>
  );
}

function FieldControl({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}