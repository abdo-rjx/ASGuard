import type { CSSProperties } from "react";
import type { StageTrace } from "../types";
import { fmtMs } from "./ui";

/** Request Inspector: renders the transaction lifecycle, lighting up stage by stage. */
export function PipelineFlow({ stages }: { stages: StageTrace[] }) {
  return (
    <div className="flow">
      {stages.map((s, i) => (
        <div className="flow-stage" key={`${s.name}-${i}`} style={{ ["--i" as string]: i } as CSSProperties}>
          <span className={`flow-node ${s.status}`} />
          <span className="flow-stage-name">{s.name}</span>
          {typeof s.risk === "number" && (
            <span className={`risk ${riskClassFor(s.risk)}`} style={{ fontSize: 11.5 }}>
              RISK {s.risk}
            </span>
          )}
          <span className="flow-latency">{fmtMs(s.latency_ms)}</span>
          {s.detail && <span className="flow-stage-detail">{s.detail}</span>}
        </div>
      ))}
    </div>
  );
}

function riskClassFor(score: number): string {
  if (score >= 90) return "risk-critical";
  if (score >= 70) return "risk-high";
  if (score >= 40) return "risk-medium";
  return "risk-low";
}

/** Bidirectional security diagram — the core product concept. */
export function GuardDiagram({ inputDecision, outputDecision }: {
  inputDecision?: string;
  outputDecision?: string;
}) {
  return (
    <div>
      <div className="guard-diagram">
        <div className="guard-node"><strong>USER</strong>client</div>
        <span className="guard-arrow">──▶</span>
        <div className="guard-node asguard">
          <strong>ASGuard</strong>
          <div className="guard-check">INPUT CHECK · {inputDecision ?? "…"}</div>
        </div>
        <span className="guard-arrow">──▶</span>
        <div className="guard-node"><strong>EXISTING AI</strong>upstream</div>
      </div>
      <div className="guard-diagram" style={{ marginTop: -6 }}>
        <div className="guard-node"><strong>USER</strong>client</div>
        <span className="guard-arrow">◀──</span>
        <div className="guard-node asguard">
          <strong>ASGuard</strong>
          <div className="guard-check">OUTPUT CHECK · {outputDecision ?? "…"}</div>
        </div>
        <span className="guard-arrow">◀──</span>
        <div className="guard-node"><strong>EXISTING AI</strong>upstream</div>
      </div>
    </div>
  );
}
