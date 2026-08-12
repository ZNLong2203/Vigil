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

// Approval, TraceSpan, Trace and IntakeArtifact were declared here to give the
// committed fixture corpus a shape. The corpus is gone and every screen now
// reads the deployed API, so the types that described authored data went with
// it; what remains are the shapes the service actually returns, declared beside
// the component that reads them.

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
