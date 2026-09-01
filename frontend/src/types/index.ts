export type Decision = "ALLOW" | "BLOCK" | "SANITIZE" | "REVIEW" | "ERROR";

export interface StageTrace {
  name: string;
  status: string;
  latency_ms: number;
  risk?: number | null;
  decision?: Decision | null;
  detail: string;
}

export interface Detection {
  detector: string;
  direction: string;
  category: string;
  detected: boolean;
  confidence: number;
  signals: string[];
  latency_ms: number;
}

export interface SecurityEvent {
  id: string;
  request_id: string;
  application_id: string | null;
  application_name: string | null;
  direction: "input" | "output";
  decision: Decision;
  risk_score: number;
  threat_types: string[];
  policy_triggered: string[];
  stages: StageTrace[];
  detections?: Detection[];
  input_latency_ms: number;
  output_latency_ms: number;
  upstream_latency_ms: number;
  total_latency_ms: number;
  upstream_status: string;
  error_code: string | null;
  content_preview: string | null;
  created_at: string;
}

export interface Metrics {
  window_hours: number;
  requests: number;
  allowed: number;
  blocked: number;
  sanitized: number;
  reviewed: number;
  threats_detected: number;
  avg_risk: number;
  avg_latency_ms: number;
  threats_by_category: Record<string, number>;
  recent_events: SecurityEvent[];
}

export interface TimeBucket {
  hour: string;
  allowed: number;
  blocked: number;
  sanitized: number;
  reviewed: number;
}

export interface Policy {
  id: string;
  direction: "input" | "output";
  category: string;
  action: string;
  threshold: number;
  enabled: boolean;
  updated_at: string;
  allowed_actions: string[];
}

export interface Application {
  id: string;
  name: string;
  upstream_url: string;
  client_api_key: string;
  has_upstream_api_key: boolean;
  auth_type: string;
  policy_profile: string;
  timeout_ms: number;
  rate_limit_rpm: number;
  logging_mode: string;
  is_active: boolean;
  status: "ONLINE" | "OFFLINE";
  created_at: string;
  last_activity_at: string | null;
  requests: number;
  avg_risk: number;
}

export interface TestResult {
  id: string;
  direction: string;
  category: string;
  description: string;
  expected_decision: string;
  actual_decision: string;
  reason: string;
  risk_score: number;
  minimum_risk: number;
  passed: boolean;
  latency_ms: number;
}

export interface TestRunSummary {
  id: string;
  started_at: string;
  total: number;
  passed: number;
  failed: number;
  results: TestResult[];
}

export interface SettingsDoc {
  security_thresholds: { block_threshold: number; review_threshold: number };
  logging: { log_level: string; log_security_events: boolean };
  privacy: { store_raw_content: boolean; retention_days: number };
  detection: { detector_failure_mode: string };
  upstream: { timeout_seconds: number };
  redaction: { style: string };
}

export interface AuditEntry {
  id: string;
  actor: string;
  action: string;
  entity: string;
  entity_id: string | null;
  detail: Record<string, unknown>;
  created_at: string;
}
