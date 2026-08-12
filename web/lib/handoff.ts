import { useRegistry } from "./registry";
import type { Department } from "./types";

/**
 * Who touched a run, in order.
 *
 * This reads the checkpoints, which already carry everything needed: each one
 * stores `payload.agent` — the agent the orchestrator handed that step to — and
 * a result with the tokens and seconds it spent. Nothing here is inferred and
 * nothing is parsed out of a step id; `delegate-0-intake-agent` is a storage
 * key, and reverse-engineering meaning from a formatted string is how a UI
 * starts lying the day someone renames a step.
 *
 * The interesting part is that this data existed from the first deployed run and
 * no screen read it. The trace view showed `api` and `worker` in its actor
 * column — the two processes that move messages around — so a viewer watching a
 * five-agent system work saw the names of the message bus instead. A system
 * whose hardest property is invisible in its own interface is, to anyone who
 * has not read the source, indistinguishable from a system that lacks it.
 */

export const DEPARTMENT_TINT: Record<Department, string> = {
  family: "var(--phosphor)",
  clinical: "var(--azure)",
  benefits: "var(--amber)",
  audit: "var(--violet)",
};

export interface Hop {
  step_id: string;
  agent: string;
  /** What this hop was for, from the step's role in the pipeline. */
  role: string;
  department: Department | null;
  seconds: number | null;
  tokens: number | null;
  tools: number | null;
  status: string;
}

interface Step {
  step_id: string;
  status?: string;
  payload?: { agent?: string } | null;
  result?: { elapsed_s?: number; tokens?: number; tools?: number } | null;
}

/** The three roles a hop can have. Derived from the step's position in the
 *  pipeline, which is a property of the design rather than of the string. */
function roleOf(stepId: string): string {
  if (stepId === "plan") return "chose who to call";
  if (stepId === "verify") return "checked the work";
  if (stepId.startsWith("delegate-")) return "did the work";
  return "ran";
}

/**
 * @param owners which department each agent belongs to. Passed in rather than
 * looked up here: that fact belongs to the deployed registry, and a copy kept in
 * this file would be one more thing that can quietly disagree with the service.
 */
export function toHops(steps: Step[], owners?: Map<string, Department>): Hop[] {
  return steps
    .map((step) => {
      const agent = step.payload?.agent;
      if (!agent) return null;
      const result = step.result ?? {};
      return {
        step_id: step.step_id,
        agent,
        role: roleOf(step.step_id),
        department: owners?.get(agent) ?? null,
        seconds: typeof result.elapsed_s === "number" ? result.elapsed_s : null,
        tokens: typeof result.tokens === "number" ? result.tokens : null,
        tools: typeof result.tools === "number" ? result.tools : null,
        status: step.status ?? "pending",
      };
    })
    .filter((h): h is Hop => h !== null);
}

/** How many distinct agents took part. Distinct, not step count: a run that
 *  calls meds-agent twice used two agents, not three. */
export function agentCount(hops: Hop[]): number {
  return new Set(hops.map((h) => h.agent)).size;
}

/** The chain for one run, with each agent's department resolved against the
 *  live registry. The hook both call sites want. */
export function useHops(steps: Step[]): Hop[] {
  const { entries } = useRegistry();
  const owners = new Map<string, Department>(entries.map((e) => [e.name, e.owner]));
  return toHops(steps, owners);
}
