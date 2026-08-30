import type { CSSProperties, ReactNode } from "react";
import { useCountUp } from "../hooks/useCountUp";

/** A number that counts up smoothly and formats with locale separators. */
export function AnimatedNumber({ value, decimals = 0 }: { value: number; decimals?: number }) {
  const animated = useCountUp(value);
  const display = decimals > 0
    ? animated.toFixed(decimals)
    : Math.round(animated).toLocaleString();
  return <>{display}</>;
}

/** Staggered fade-up reveal — set --i for the delay slot. */
export function Reveal({ i = 0, children, className = "", style }: {
  i?: number;
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div className={`reveal ${className}`} style={{ "--i": i, ...style } as CSSProperties}>
      {children}
    </div>
  );
}

/** Small gold chip used for threat-type labels. */
export function Chip({ children }: { children: ReactNode }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 10.5,
        padding: "1px 7px",
        borderRadius: 3,
        border: "1px solid var(--border-strong)",
        color: "var(--muted)",
        background: "var(--panel-3)",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </span>
  );
}
