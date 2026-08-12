/**
 * The agent registry, read from the service, positioned by this file.
 *
 * This module used to hold a hand-written copy of the catalogue. That copy was
 * the fleet screen's only source, so the page showed five agents, their scopes
 * and their version history whether or not any of it still matched what was
 * deployed — including the rejected version, the single most load-bearing claim
 * the project makes. A second copy of a fact is a fact that can be wrong.
 *
 * What stays here is the part the API has no business knowing: where each box
 * sits. Coordinates are hand-placed rather than force-directed because a demo
 * needs the same frame on every take, and a graph that rearranges itself between
 * renders cannot be filmed twice.
 */

import { useLive, type Live } from "./live";
import type { AgentName, Department } from "./types";

export interface VersionRecord {
  id: string;
  version: string;
  status?: "promoted" | "rejected" | "superseded";
  eval_score?: number;
  anti_gaming_passed?: boolean;
  refusal_rate_before?: number;
  refusal_rate_after?: number;
  at?: string;
  /** Present on rejections. This field is the point of the whole mechanism. */
  reason?: string;
  per_case?: unknown;
}

/** As the API returns it. */
export interface ApiAgent {
  /** The tool names build_belt actually assembles for this agent. */
  tools?: string[];
  name: AgentName;
  version: string;
  owner: Department;
  summary: string;
  accepts: string;
  returns: string;
  tool_scopes: string[];
  callable_by: AgentName[];
  eval: { suite: string; score: number; cases: number; anti_gaming_passed: boolean };
  versions: VersionRecord[];
}

/** An agent plus the one thing the API does not supply: where to draw it. */
export interface RegistryEntry extends ApiAgent {
  capability: { input: string; output: string };
  history: VersionRecord[];
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

/** Layout only. An agent with no entry here is drawn off to the side rather
 *  than dropped — a fleet that grows should not silently lose a member. */
const POSITIONS: Record<string, { x: number; y: number }> = {
  orchestrator: { x: 500, y: 292 },
  "intake-agent": { x: 140, y: 108 },
  "meds-agent": { x: 380, y: 108 },
  "benefits-agent": { x: 620, y: 108 },
  watchdog: { x: 860, y: 108 },
};

const FALLBACK_POS = { x: 500, y: 108 };

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

/** The registry, live. Polled slowly: a catalogue changes when something is
 *  promoted, which is minutes apart at best. */
export function useRegistry(): Live<{ agents: ApiAgent[]; scope_owners: ScopeOwners }> & {
  entries: RegistryEntry[];
  scopeOwners: ScopeOwners;
} {
  const live = useLive<{ agents: ApiAgent[]; scope_owners: ScopeOwners }>("/registry", 60_000);
  const entries = (live.data?.agents ?? []).map((agent) => ({
    ...agent,
    capability: { input: agent.accepts, output: agent.returns },
    history: agent.versions,
    pos: POSITIONS[agent.name] ?? FALLBACK_POS,
  }));
  return { ...live, entries, scopeOwners: live.data?.scope_owners ?? {} };
}

/**
 * What one agent cannot reach, derived from the deployed registry.
 *
 * The fleet screen used to draw a hand-written denial event: benefits-agent
 * reaching for a clinical note and being refused. The refusal mechanism is real
 * and tested — but that picture was still the wrong one, because a runtime
 * denial is the *second* layer, and the second layer almost never fires. The
 * first layer never hands the agent the tool at all, so there is nothing to
 * call and no event to record. Drawing an event that the design exists to
 * prevent puts the weakest possible evidence on the screen's central claim.
 *
 * So this computes the boundary itself: for each department, the scopes it owns
 * that this agent does not hold, and therefore the tools it is never given. That
 * is a fact about the deployment, it comes from the deployment, and it is true
 * whether or not anything has been refused today.
 */
export function useBoundaries(agent: RegistryEntry | undefined, scopeOwners: ScopeOwners) {
  if (!agent) return [] as DeniedEdge[];

  const held = new Set(agent.tool_scopes);
  const byDepartment = new Map<Department, string[]>();

  for (const [scope, owner] of Object.entries(scopeOwners)) {
    if (!owner || owner === agent.owner || held.has(scope)) continue;
    byDepartment.set(owner as Department, [...(byDepartment.get(owner as Department) ?? []), scope]);
  }

  return [...byDepartment.entries()].map(([department, scopes]) => ({
    from: agent.name,
    to_department: department,
    resource: scopes.join(", "),
    at: "",
    outcome: `${agent.name} is never handed a tool requiring ${scopes.join(" or ")}. The belt is assembled from its registry scopes, so there is no declaration for it to call — and if that wiring were ever wrong, every call is re-checked against the same scopes before it runs.`,
  }));
}

export type ScopeOwners = Record<string, string | null>;

/** Runtime refusals, if any have happened. Layer two doing its job leaves a
 *  record; an empty list means layer one has held, which is the normal case. */
export function useRuntimeDenials(): DeniedEdge[] {
  const live = useLive<{ entries: AuditRow[] }>("/audit?limit=200", 30_000);
  const rows = live.data?.entries ?? [];

  return rows
    .filter((e) => e.action === "tool.denied" || e.action === "delegation.not_permitted")
    .map((e) => {
      const details = e.details ?? {};
      return {
        from: (e.actor ?? "unknown") as AgentName,
        to_department: (details.boundary ?? "clinical") as Department,
        resource: String(details.tool ?? details.requested ?? "a tool"),
        at: e.at ?? "",
        outcome: `Refused at call time. ${details.tool ?? "The tool"} requires ${details.required_scope ?? "a scope"}, which belongs to the ${details.boundary ?? "another"} boundary.`,
      };
    });
}

interface AuditRow {
  actor?: string;
  action?: string;
  at?: string;
  details?: Record<string, string | undefined>;
}
