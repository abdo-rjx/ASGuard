import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useState, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { connection } from "../services/connection";
import { isDesktop } from "../services/api";

const NAV = [
  { to: "/", label: "Dashboard", icon: "▣" },
  { to: "/events", label: "Security Events", icon: "⚡" },
  { to: "/input-security", label: "Input Security", icon: "▼" },
  { to: "/output-security", label: "Output Security", icon: "▲" },
  { to: "/policies", label: "Policies", icon: "§" },
  { to: "/applications", label: "Applications", icon: "◈" },
  { to: "/testing", label: "Testing", icon: "✓" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

function LiveClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return <span>{now.toLocaleTimeString([], { hour12: false })}</span>;
}

/** LIVE (backend connected) / DEMO (offline simulator) / connecting pill. */
function ConnectionPill() {
  const status = useSyncExternalStore(connection.subscribe, connection.get);
  if (status === "live") {
    return (
      <span className="live-pill">
        <span className="live-dot" />
        LIVE
      </span>
    );
  }
  if (status === "demo") {
    return (
      <span className="live-pill demo-pill" title="No backend reachable — showing simulated data. Configure the backend URL in Settings.">
        <span className="live-dot" style={{ background: "var(--gold)" }} />
        DEMO
      </span>
    );
  }
  return (
    <span className="live-pill offline-pill" title="Searching for the ASGuard backend…">
      <span className="live-dot" style={{ background: "var(--faint)" }} />
      ···
    </span>
  );
}

export function Layout({ title, children }: { title: string; children: ReactNode }) {
  const location = useLocation();
  const pageKey = location.pathname;
  const lastSegment = location.pathname === "/" ? "" : location.pathname.split("/").slice(-1)[0];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <img src="/asguard-shield.svg" alt="ASGuard shield logo" className="brand-logo" />
          </div>
          <div>
            <div className="brand-name">
              <span className="accent">AS</span>GUARD
            </div>
            <div className="brand-sub">AI Security Firewall</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/"}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {isDesktop ? (
            <>
              desktop console · v0.1.0
              <br />
              fedora · windows · mac
            </>
          ) : (
            <>
              v0.1.0 · middleware
              <br />
              bidirectional protection
            </>
          )}
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <span className="topbar-title">{title}</span>
          <span className="topbar-meta">
            <ConnectionPill />
            <LiveClock />
            <span>ASGuard{lastSegment ? ` · ${lastSegment}` : ""}</span>
          </span>
        </header>
        <main className="content">
          {/* key on pathname re-triggers the page-enter animation on navigation */}
          <div className="page-enter" key={pageKey}>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

