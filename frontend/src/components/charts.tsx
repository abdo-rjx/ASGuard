/** Hand-rolled animated SVG charts — no chart library, real data only. */

import { useEffect, useState } from "react";
import type { TimeBucket } from "../types";

const COLORS = {
  allowed: "var(--patina)",
  blocked: "var(--block)",
  sanitized: "var(--gold)",
  reviewed: "var(--review)",
};

export function StackedBarChart({ data, height = 180 }: { data: TimeBucket[]; height?: number }) {
  const width = 720;
  const pad = { top: 8, right: 4, bottom: 20, left: 30 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const max = Math.max(1, ...data.map((d) => d.allowed + d.blocked + d.sanitized + d.reviewed));
  const bw = innerW / Math.max(1, data.length);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "auto" }} role="img" aria-label="Requests over time">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={pad.left} x2={width - pad.right} y1={pad.top + innerH * (1 - f)} y2={pad.top + innerH * (1 - f)} stroke="var(--hairline)" />
          <text x={pad.left - 4} y={pad.top + innerH * (1 - f) + 3} textAnchor="end" fontSize="9" fill="var(--faint)" fontFamily="var(--font-mono)">
            {Math.round(max * f)}
          </text>
        </g>
      ))}
      {data.map((d, i) => {
        const segments: Array<[number, string]> = [
          [d.allowed, COLORS.allowed],
          [d.sanitized, COLORS.sanitized],
          [d.blocked, COLORS.blocked],
          [d.reviewed, COLORS.reviewed],
        ];
        let acc = 0;
        const x = pad.left + i * bw + bw * 0.15;
        const w = bw * 0.7;
        return (
          <g key={d.hour}>
            {segments.map(([value, color], si) => {
              if (value <= 0) return null;
              const h = (value / max) * innerH;
              acc += h;
              return (
                <rect
                  key={si}
                  className="chart-bar"
                  style={{ animationDelay: `${Math.min(i * 30, 600)}ms` }}
                  x={x}
                  y={pad.top + innerH - acc}
                  width={w}
                  height={h}
                  fill={color}
                  rx={1}
                >
                  <title>{`${d.hour} — ${value}`}</title>
                </rect>
              );
            })}
            {i % 4 === 0 && (
              <text x={x + w / 2} y={height - 6} textAnchor="middle" fontSize="9" fill="var(--faint)" fontFamily="var(--font-mono)">
                {d.hour.slice(11, 16)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export function HBarChart({ entries, total }: { entries: Array<{ label: string; value: number }>; total?: number }) {
  const max = Math.max(1, ...entries.map((e) => e.value));
  const sum = total ?? entries.reduce((a, e) => a + e.value, 0);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {entries.map((e, i) => (
        <div
          key={e.label}
          className="reveal"
          style={{ ["--i" as string]: i, display: "grid", gridTemplateColumns: "170px 1fr 52px", alignItems: "center", gap: 10 }}
        >
          <span style={{ fontSize: 12.5, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>{e.label}</span>
          <div style={{ background: "var(--panel-3)", borderRadius: 3, height: 12, overflow: "hidden" }}>
            <div
              className="chart-hbar-fill"
              style={{
                width: `${(e.value / max) * 100}%`,
                height: "100%",
                background: "linear-gradient(90deg, var(--gold-deep), var(--gold))",
                borderRadius: 3,
                animationDelay: `${i * 90}ms`,
              }}
            />
          </div>
          <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", textAlign: "right", color: "var(--muted)", fontVariantNumeric: "tabular-nums" }}>
            {sum > 0 ? `${Math.round((e.value / sum) * 100)}%` : e.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function Donut({ segments, centerLabel, centerValue }: {
  segments: Array<{ label: string; value: number; color: string }>;
  centerLabel: string;
  centerValue: string | number;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const total = segments.reduce((a, s) => a + s.value, 0);
  const r = 52;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 22, flexWrap: "wrap" }}>
      <svg width={140} height={140} viewBox="0 0 140 140" role="img" aria-label={centerLabel}>
        <circle cx={70} cy={70} r={r} fill="none" stroke="var(--panel-3)" strokeWidth={13} />
        {total > 0 &&
          segments.map((s) => {
            const frac = s.value / total;
            const targetOffset = -offset;
            offset += frac * c;
            return (
              <circle
                key={s.label}
                className="chart-seg"
                cx={70}
                cy={70}
                r={r}
                fill="none"
                stroke={s.color}
                strokeWidth={13}
                strokeDasharray={`${Math.max(0, frac * c - 1.5)} ${c}`}
                strokeDashoffset={mounted ? targetOffset : c}
                transform="rotate(-90 70 70)"
              >
                <title>{`${s.label}: ${s.value}`}</title>
              </circle>
            );
          })}
        <text x={70} y={68} textAnchor="middle" fontSize={22} fontWeight={700} fill="var(--text)" fontFamily="var(--font-mono)">
          {centerValue}
        </text>
        <text x={70} y={85} textAnchor="middle" fontSize={8.5} fill="var(--faint)" letterSpacing={1.5}>
          {centerLabel.toUpperCase()}
        </text>
      </svg>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {segments.map((s) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
            <span className="stat-dot" style={{ background: s.color }} />
            <span style={{ color: "var(--muted)" }}>{s.label}</span>
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text)" }}>{s.value.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
