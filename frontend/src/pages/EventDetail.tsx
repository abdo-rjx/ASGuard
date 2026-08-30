import type { SecurityEvent } from "../types";
import { api } from "../services/api";
import { PipelineFlow } from "../components/PipelineFlow";
import { Card, DecisionBadge, DirBadge, RiskValue, fmtMs, riskClass } from "../components/ui";
import { useApi } from "../hooks/useApi";

export function EventDetailBody({ event }: { event: SecurityEvent }) {
  const detected = (event.detections ?? []).filter((d) => d.detected);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <dl className="kv">
        <dt>Event ID</dt><dd>{event.id}</dd>
        <dt>Request ID</dt><dd>{event.request_id}</dd>
        <dt>Timestamp</dt><dd>{new Date(event.created_at).toLocaleString()}</dd>
        <dt>Direction</dt><dd><DirBadge direction={event.direction} /></dd>
        <dt>Application</dt><dd>{event.application_name ?? "—"}</dd>
        <dt>Risk Score</dt><dd><span className={`risk ${riskClass(event.risk_score)}`}>{event.risk_score}/100</span></dd>
        <dt>Decision</dt><dd><DecisionBadge decision={event.decision} /></dd>
        <dt>Policy Triggered</dt>
        <dd>{event.policy_triggered.length ? event.policy_triggered.join(", ") : "—"}</dd>
        <dt>Upstream Status</dt><dd>{event.upstream_status}{event.error_code ? ` · ${event.error_code}` : ""}</dd>
        <dt>Processing Latency</dt>
        <dd>
          total {fmtMs(event.total_latency_ms)} (input {fmtMs(event.input_latency_ms)} · upstream{" "}
          {fmtMs(event.upstream_latency_ms)} · output {fmtMs(event.output_latency_ms)})
        </dd>
      </dl>

      {event.threat_types.length > 0 && (
        <Card title="Threat Detection">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {detected.map((d) => (
              <div key={d.detector} style={{ display: "grid", gridTemplateColumns: "220px 1fr auto", gap: 10, alignItems: "center" }}>
                <span className="mono" style={{ fontFamily: "var(--font-mono)", fontSize: 12.5 }}>{d.detector}</span>
                <span style={{ color: "var(--faint)", fontSize: 12 }}>{d.signals.join(", ")}</span>
                <RiskValue score={Math.round(d.confidence * 100)} />
              </div>
            ))}
            <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8, display: "grid", gridTemplateColumns: "220px 1fr auto" }}>
              <span style={{ fontWeight: 600 }}>Final Risk</span>
              <span />
              <span className={`risk ${riskClass(event.risk_score)}`}>{event.risk_score}/100 · {event.decision}</span>
            </div>
          </div>
        </Card>
      )}

      <Card title="Transaction Lifecycle (Request Inspector)">
        <PipelineFlow stages={event.stages} />
        <div style={{ marginTop: 12 }}>
          <a href={`/inspector/${event.id}`} style={{ color: "var(--info)", fontSize: 13 }}>
            Open full request inspector →
          </a>
        </div>
      </Card>

      {event.content_preview && (
        <Card title="Content Preview (logging enabled for this application)">
          <code className="inline" style={{ whiteSpace: "pre-wrap", display: "block", padding: "10px 12px" }}>
            {event.content_preview}
          </code>
        </Card>
      )}
    </div>
  );
}

export function EventDetailPage() {
  // The :id param is read from the URL by React Router; fetch directly.
  const id = window.location.pathname.split("/").pop() ?? "";
  const { data: event, error, loading } = useApi<SecurityEvent>(() => api.event(id), [id]);
  if (loading) return <span className="spinning" />;
  if (error || !event) return <div className="empty">Event not found.</div>;
  return <EventDetailBody event={event} />;
}
