/** Minimal fetch-based API client for the ASGuard dashboard. */

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

const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
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
