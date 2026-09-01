/**
 * Minimal fetch-based API client for the ASGuard dashboard.
 *
 * Desktop mode (Tauri): talks to a user-configured ASGuard backend
 * (default http://127.0.0.1:8000). If the backend is unreachable, requests
 * transparently fall back to the built-in offline demo simulator and the
 * connection pill in the sidebar switches from LIVE to DEMO.
 *
 * Browser mode: same-origin requests (vite dev proxy or FastAPI static mount).
 */

import type {
  Application,
  AuditEntry,
  Metrics,
  Policy,
  SecurityEvent,
  SettingsDoc,
  TestResult,
  TestRunSummary,
  TimeBucket,
} from "../types";
import { connection } from "./connection";
import { demoHandle } from "./demo";

/** True when running inside the Tauri desktop shell. */
export const isDesktop =
  typeof window !== "undefined" &&
  (window.location.protocol === "tauri:" || window.location.hostname === "tauri.localhost");

const BACKEND_KEY = "asguard.backendUrl";
const DEMO_KEY = "asguard.forceDemo";

const defaultBackendUrl = (): string => (isDesktop ? "http://127.0.0.1:8000" : "");

let backendUrl = localStorage.getItem(BACKEND_KEY) ?? defaultBackendUrl();
let forceDemo = localStorage.getItem(DEMO_KEY) === "1";

/** Desktop-only connection configuration (persisted to localStorage). */
export const desktopConfig = {
  get backendUrl(): string {
    return backendUrl;
  },
  setBackendUrl(url: string): void {
    backendUrl = url.trim().replace(/\/+$/, "");
    if (!backendUrl || backendUrl === defaultBackendUrl()) localStorage.removeItem(BACKEND_KEY);
    else localStorage.setItem(BACKEND_KEY, backendUrl);
  },
  get forceDemo(): boolean {
    return forceDemo;
  },
  setForceDemo(on: boolean): void {
    forceDemo = on;
    if (on) localStorage.setItem(DEMO_KEY, "1");
    else localStorage.removeItem(DEMO_KEY);
  },
};

/** Probe the configured backend; returns the resulting connection status. */
export async function probeBackend(): Promise<"live" | "demo"> {
  if (forceDemo) {
    connection.set("demo");
    return "demo";
  }
  try {
    const res = await fetch(backendUrl + "/health", { signal: AbortSignal.timeout(3000) });
    connection.set(res.ok ? "live" : "demo");
    return res.ok ? "live" : "demo";
  } catch {
    connection.set("demo");
    return "demo";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (forceDemo) {
    connection.set("demo");
    return demoHandle<T>(path, init);
  }
  try {
    const response = await fetch(backendUrl + path, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    connection.set("live");
    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body.detail ?? body.error?.message ?? JSON.stringify(body);
      } catch {
        /* keep statusText */
      }
      throw new Error(`${response.status}: ${detail}`);
    }
    return (await response.json()) as T;
  } catch (err) {
    // Network-layer failure (backend down) → transparent offline demo mode.
    if (err instanceof TypeError) {
      connection.set("demo");
      return demoHandle<T>(path, init);
    }
    throw err;
  }
}

export const api = {
  // dashboard
  metrics: (windowHours = 24) =>
    request<Metrics>(`/api/dashboard/metrics?window_hours=${windowHours}`),
  timeseries: (hours = 24) =>
    request<TimeBucket[]>(`/api/dashboard/timeseries?hours=${hours}`),

  // events
  events: (params: { limit?: number; offset?: number; direction?: string; decision?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.direction) q.set("direction", params.direction);
    if (params.decision) q.set("decision", params.decision);
    return request<{ total: number; events: SecurityEvent[] }>(`/api/events?${q}`);
  },
  event: (id: string) => request<SecurityEvent>(`/api/events/${id}`),

  // policies
  policies: () => request<{ policies: Policy[] }>("/api/policies"),
  updatePolicy: (id: string, patch: { action: string; threshold: number; enabled: boolean; reason?: string }) =>
    request<Policy>(`/api/policies/${id}`, { method: "PUT", body: JSON.stringify(patch) }),

  // applications
  applications: () => request<{ applications: Application[] }>("/api/applications"),
  createApplication: (payload: Partial<Application> & { name: string; upstream_url: string }) =>
    request<Application>("/api/applications", { method: "POST", body: JSON.stringify(payload) }),
  updateApplication: (id: string, payload: Record<string, unknown>) =>
    request<Application>(`/api/applications/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteApplication: (id: string) =>
    request<{ deleted: boolean }>(`/api/applications/${id}`, { method: "DELETE" }),

  // testing
  runTests: () =>
    request<{ run_id: string; total: number; passed: number; failed: number; results: TestResult[] }>(
      "/api/testing/run",
      { method: "POST" },
    ),
  testResults: () => request<{ runs: TestRunSummary[] }>("/api/testing/results"),

  // settings + audit
  settings: () => request<SettingsDoc>("/api/settings"),
  updateSettings: (data: Record<string, unknown>) =>
    request<SettingsDoc>("/api/settings", { method: "PUT", body: JSON.stringify(data) }),
  audit: () => request<{ entries: AuditEntry[] }>("/api/audit"),
};
