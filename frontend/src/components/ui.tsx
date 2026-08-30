import type { ReactNode } from "react";
import type { Decision } from "../types";
import { AnimatedNumber } from "../components/motion";

export function riskClass(score: number): string {
  if (score >= 90) return "risk-critical";
  if (score >= 70) return "risk-high";
  if (score >= 40) return "risk-medium";
  return "risk-low";
}

export function Card({ title, actions, children, bodyClass }: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  bodyClass?: string;
}) {
  return (
    <div className="card">
      {title && (
        <div className="card-header">
          <span className="card-title">{title}</span>
          {actions}
        </div>
      )}
      <div className={`card-body ${bodyClass ?? ""}`}>{children}</div>
    </div>
  );
}

export function StatCard({ label, value, dotColor, sub, decimals }: {
  label: string;
  value: string | number;
  dotColor?: string;
  sub?: string;
  decimals?: number;
}) {
  return (
    <div className="card stat">
      <div className="stat-label">
        {dotColor && <span className="stat-dot" style={{ background: dotColor }} />}
        {label}
      </div>
      <div className="stat-value">
        {typeof value === "number"
          ? <AnimatedNumber value={value} decimals={decimals} />
          : value}
      </div>
      {sub && <div style={{ fontSize: 11, color: "var(--faint)" }}>{sub}</div>}
    </div>
  );
}

export function DecisionBadge({ decision }: { decision: Decision | string }) {
  return <span className={`badge badge-${decision}`}>{decision}</span>;
}

export function DirBadge({ direction }: { direction: string }) {
  return <span className={`dir dir-${direction}`}>{direction.toUpperCase()}</span>;
}

export function RiskValue({ score }: { score: number }) {
  return <span className={`risk ${riskClass(score)}`}>{score}</span>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export function Alert({ kind, children }: { kind: "error" | "ok" | "info"; children: ReactNode }) {
  return <div className={`alert alert-${kind}`}>{children}</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function Drawer({ open, onClose, children }: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <button className="drawer-close" onClick={onClose} aria-label="Close">×</button>
        {children}
      </div>
    </>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && <span className="hint">{hint}</span>}
    </div>
  );
}

export function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return "just now";
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function clockTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour12: false });
}

export function fmtMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`;
  return `${ms.toFixed(1)}ms`;
}
