/**
 * Shapes mirror the Firestore collections written by src/vigil/state.py.
 * Keeping them aligned now means swapping mock data for the real API later is a
 * fetch call, not a rewrite.
 */

export type Department = "family" | "clinical" | "benefits" | "audit";

export type AgentName =
  | "orchestrator"
  | "intake-agent"
  | "meds-agent"
  | "benefits-agent"
  | "watchdog";

export type RunStatus = "running" | "done" | "failed" | "awaiting_approval";

/** Mirrors the `decision` field on an audit entry. */
export type Decision =
  | "accepted"
  | "done"
  | "skipped"
  | "failed"
  | "blocked"
  | "denied"
  | "escalated"
  | "awaiting_approval";

export interface Run {
  run_id: string;
  kind: string;
  subject: string;
  status: RunStatus;
  cursor: string | null;
  trace_id: string;
  created_at: string;
  updated_at: string;
}

export interface TimelineEvent {
  id: string;
  at: string;
  department: Department;
  actor: AgentName | "carer";
  title: string;
  detail?: string;
  decision: Decision;
  /** Where this came from — every remembered fact carries its origin. */
  source_uri?: string;
  confidence?: number;
  run_id?: string;
  /** Set when this event contradicts an earlier one rather than replacing it. */
  conflicts_with?: string;
}

export interface Approval {
  id: string;
  requested_by: AgentName;
  department: Department;
  action: string;
  rationale: string;
  /** Why the policy engine refused to let this proceed unattended. */
  gate_reason: string;
  risk: "low" | "medium" | "high";
  confidence: number;
  evidence: { label: string; source_uri: string }[];
  requested_at: string;
  run_id: string;
}

export interface TraceSpan {
  span_id: string;
  parent_id: string | null;
  name: string;
  actor: AgentName | "api" | "policy" | "guardrail";
  department?: Department;
  model?: string;
  tokens?: number;
  cost_usd?: number;
  duration_ms: number;
  decision: Decision;
  note?: string;
  depth: number;
}

export interface Trace {
  trace_id: string;
  run_id: string;
  started_at: string;
  total_ms: number;
  total_tokens: number;
  total_cost_usd: number;
  outcome: Decision;
  headline: string;
  spans: TraceSpan[];
}

export interface IntakeArtifact {
  id: string;
  kind: "photo" | "voice_note" | "document";
  filename: string;
  /** What makes this input hard — the messiness is the point. */
  difficulty: string;
  bytes: number;
  extracted: Record<string, string | number | boolean | null>;
  redactions: number;
  blocked?: { reason: string; excerpt: string };
  duration_ms: number;
  model: string;
}

export const DEPARTMENT_LABEL: Record<Department, string> = {
  family: "Family",
  clinical: "Clinical",
  benefits: "Benefits",
  audit: "Audit",
};

export const DECISION_CHIP: Record<Decision, { className: string; glyph: string }> = {
  accepted: { className: "chip chip-info", glyph: "→" },
  done: { className: "chip chip-ok", glyph: "✓" },
  skipped: { className: "chip chip-muted", glyph: "≡" },
  failed: { className: "chip chip-deny", glyph: "✗" },
  blocked: { className: "chip chip-deny", glyph: "⊘" },
  denied: { className: "chip chip-deny", glyph: "⊘" },
  escalated: { className: "chip chip-wait", glyph: "↑" },
  awaiting_approval: { className: "chip chip-wait", glyph: "⏸" },
};
