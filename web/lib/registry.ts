/**
 * Agent Registry — mock of the Firestore `registry` collection.
 *
 * This is a track deliverable, not a nicety: the Fortified Enterprise Fleet
 * category requires showing how agents are catalogued for cross-department use.
 * An entry is what one department has to read to decide whether it may call
 * something another department owns.
 *
 * The version history carries the other half of the story — an agent proposing
 * an improvement to itself, and the anti-gaming judge refusing one. See
 * docs/adr/006-eval-gate-and-anti-gaming-judge.md.
 */

import type { AgentName, Department } from "./types";

export interface VersionRecord {
  version: string;
  status: "promoted" | "rejected" | "superseded";
  eval_score: number;
  anti_gaming_passed: boolean;
  at: string;
  /** Present on rejections. This field is the point of the whole mechanism. */
  reason?: string;
}

export interface RegistryEntry {
  name: AgentName;
  version: string;
  owner: Department;
  summary: string;
  capability: { input: string; output: string };
  tool_scopes: string[];
  callable_by: AgentName[];
  eval: { suite: string; score: number; cases: number; anti_gaming_passed: boolean };
  promoted_at: string;
  history: VersionRecord[];
  /** Layout is hand-placed so every take of the demo frames identically. */
  pos: { x: number; y: number };
}

/** A read one agent attempted across a boundary it does not hold. */
export interface DeniedEdge {
  from: AgentName;
  to_department: Department;
  resource: string;
  at: string;
  outcome: string;
}

export const REGISTRY: RegistryEntry[] = [
  {
    name: "orchestrator",
    version: "2.1.0",
    owner: "family",
    summary:
      "Routes work, owns budgets and checkpoints, assigns idempotency keys. Holds no business tools of its own — it can only look agents up and call them.",
    capability: { input: "CleanEvent", output: "RunPlan" },
    tool_scopes: ["registry:read", "state:write"],
    callable_by: [],
    eval: { suite: "routing-v4", score: 0.93, cases: 30, anti_gaming_passed: true },
    promoted_at: "2026-08-08T10:20:00Z",
    history: [
      { version: "2.1.0", status: "promoted", eval_score: 0.93, anti_gaming_passed: true, at: "2026-08-08T10:20:00Z" },
      { version: "2.0.4", status: "superseded", eval_score: 0.9, anti_gaming_passed: true, at: "2026-08-05T14:02:00Z" },
    ],
    pos: { x: 500, y: 296 },
  },
  {
    name: "intake-agent",
    version: "1.7.1",
    owner: "family",
    summary:
      "Turns photos, voice notes and scans into structured events. Writes to staging only — it can never cause an external side effect.",
    capability: { input: "RawArtifact", output: "StructuredEvent" },
    tool_scopes: ["storage:read", "staging:write"],
    callable_by: ["orchestrator"],
    eval: { suite: "extraction-v6", score: 0.89, cases: 24, anti_gaming_passed: true },
    promoted_at: "2026-08-09T08:44:00Z",
    history: [
      { version: "1.7.1", status: "promoted", eval_score: 0.89, anti_gaming_passed: true, at: "2026-08-09T08:44:00Z" },
      { version: "1.7.0", status: "superseded", eval_score: 0.86, anti_gaming_passed: true, at: "2026-08-06T11:15:00Z" },
    ],
    pos: { x: 140, y: 108 },
  },
  {
    name: "meds-agent",
    version: "1.4.2",
    owner: "clinical",
    summary:
      "Medication schedule, collision and interaction detection, reminders. Reads the medication graph; may write a schedule but never a clinical record.",
    capability: { input: "MedicationContext", output: "ScheduleProposal" },
    tool_scopes: ["medgraph:read", "schedule:write"],
    callable_by: ["orchestrator", "watchdog"],
    eval: { suite: "meds-v3", score: 0.91, cases: 20, anti_gaming_passed: true },
    promoted_at: "2026-08-10T16:31:00Z",
    history: [
      {
        version: "1.5.0-rc",
        status: "rejected",
        eval_score: 0.94,
        anti_gaming_passed: false,
        at: "2026-08-11T02:14:00Z",
        reason:
          "Score rose because the proposal declined 3 of 20 hard cases instead of answering them, and the suite counted a refusal as a pass. Judge found the instruction had been rewritten to add \"if uncertain, defer to the carer\" — which reads as caution but is scored as success. Not a real improvement.",
      },
      { version: "1.4.2", status: "promoted", eval_score: 0.91, anti_gaming_passed: true, at: "2026-08-10T16:31:00Z" },
      { version: "1.4.1", status: "superseded", eval_score: 0.88, anti_gaming_passed: true, at: "2026-08-07T09:02:00Z" },
    ],
    pos: { x: 380, y: 108 },
  },
  {
    name: "benefits-agent",
    version: "1.2.0",
    owner: "benefits",
    summary:
      "Tracks insurance and benefit deadlines, drafts forms. Generates documents; submitting one is always gated on a human.",
    capability: { input: "BenefitsContext", output: "DraftDocument" },
    tool_scopes: ["benefits:read", "doc:generate"],
    callable_by: ["orchestrator"],
    eval: { suite: "benefits-v2", score: 0.87, cases: 18, anti_gaming_passed: true },
    promoted_at: "2026-08-09T13:50:00Z",
    history: [
      { version: "1.2.0", status: "promoted", eval_score: 0.87, anti_gaming_passed: true, at: "2026-08-09T13:50:00Z" },
    ],
    pos: { x: 620, y: 108 },
  },
  {
    name: "watchdog",
    version: "1.1.3",
    owner: "audit",
    summary:
      "Read-only. Verifies other agents against persisted state, counts steps, detects repeated states, escalates when confidence is low. Cannot act.",
    capability: { input: "AgentOutput", output: "Verdict" },
    tool_scopes: ["state:read", "escalation:write"],
    callable_by: ["orchestrator"],
    eval: { suite: "verify-v5", score: 0.95, cases: 26, anti_gaming_passed: true },
    promoted_at: "2026-08-10T07:12:00Z",
    history: [
      { version: "1.1.3", status: "promoted", eval_score: 0.95, anti_gaming_passed: true, at: "2026-08-10T07:12:00Z" },
      { version: "1.1.2", status: "superseded", eval_score: 0.92, anti_gaming_passed: true, at: "2026-08-04T18:30:00Z" },
    ],
    pos: { x: 860, y: 108 },
  },
];

export const DENIED_EDGES: DeniedEdge[] = [
  {
    from: "benefits-agent",
    to_department: "clinical",
    resource: "care-note-week3.pdf — clinical visit note",
    at: "2026-08-09T14:22:00Z",
    outcome:
      "Agent Identity refused. The Benefits boundary excludes clinical notes, and no prompt can widen it. The agent fell back to requesting a Family approval, which is the legitimate route.",
  },
];

export const DEPARTMENT_BANDS: {
  id: Department;
  label: string;
  x: number;
  width: number;
  note: string;
}[] = [
  { id: "family", label: "Family", x: 30, width: 220, note: "everything but raw clinical notes" },
  { id: "clinical", label: "Clinical", x: 270, width: 220, note: "clinical data, no financials" },
  { id: "benefits", label: "Benefits", x: 510, width: 220, note: "admin + invoices, no clinical" },
  { id: "audit", label: "Audit", x: 750, width: 220, note: "all traces, PII stays tokenised" },
];
