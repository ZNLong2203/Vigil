"use client";

import { useLive } from "@/lib/live";
import { ErrorScreen, LoadingScreen } from "@/components/Screen";
import { Handoff } from "@/components/Handoff";
import { agentCount, useHops } from "@/lib/handoff";

/**
 * One run's reasoning chain, as a tree, read from the deployed audit trail.
 *
 * The hierarchy is the point and it is not decoration: an agent hop owns the
 * decisions taken inside it, and a flat list of timestamps makes the reader
 * reconstruct that ownership in their head. Nesting says directly that the two
 * external effects belong to meds-agent's hop and the escalation belongs to the
 * watchdog's.
 *
 * Structure comes from the data rather than from a shape written by hand. Each
 * checkpoint carries the agent it was handed to and the window it ran in, so an
 * audit entry nests under the hop whose window contains it, falling back to a
 * match on actor for entries written just after a hop closed. What belongs to no
 * hop — the event arriving, the run finishing — sits at the root, which is
 * exactly where those things happened.
 *
 * Dense, because the point of an operator surface is seeing the whole run at
 * once. What keeps it legible is that there is one primary read, the path down
 * the tree, carried by indentation and the duration bars; everything an engineer
 * needs but a reader does not sits at --text-2 until the row is hovered.
 *
 * Refusals are the rows worth finding, so they are the rows that carry colour.
 * A trace where nothing was refused should look uneventful; that is information
 * too.
 */

const ACTOR_TINT: Record<string, string> = {
  api: "var(--text-2)",
  worker: "var(--text-2)",
  orchestrator: "var(--phosphor)",
  "intake-agent": "var(--phosphor)",
  "meds-agent": "var(--azure)",
  "benefits-agent": "var(--amber)",
  watchdog: "var(--violet)",
};

/** Which hop, if any, owns this decision. */
function ownerOf(entry: Entry, steps: Step[]): string | null {
  const at = entry.at ?? "";
  const containing = steps.find(
    (s) => s.started_at && at >= s.started_at && (!s.completed_at || at <= s.completed_at),
  );
  if (containing) return containing.step_id;

  // Written in the moment after the hop closed — the watchdog's own summary of
  // its verification lands here. Actor is the right tiebreak; time alone would
  // orphan it.
  const byActor = steps.find((s) => s.payload?.agent === entry.actor);
  return byActor?.step_id ?? null;
}

function Bar({ seconds, longest }: { seconds: number; longest: number }) {
  const pct = Math.max(2, (seconds / longest) * 100);
  return (
    <div
      className="h-1.5 w-full rounded-full bg-[var(--bg-3)] overflow-hidden"
      title={`${seconds.toFixed(1)} s`}
    >
      <div
        className="h-full rounded-full"
        style={{
          width: `${pct}%`,
          background: "color-mix(in oklab, var(--azure) 70%, transparent)",
        }}
      />
    </div>
  );
}

function DecisionRow({ entry, depth }: { entry: Entry; depth: number }) {
  const style = DECISION_STYLE[entry.decision] ?? DECISION_STYLE.done;
  const notable = ["blocked", "denied", "escalated", "failed"].includes(entry.decision);
  const text = detail(entry);

  return (
    <div
      className="row grid-cols-[4.5rem_1fr]"
      style={
        notable ? { background: "color-mix(in oklab, var(--rose) 5%, transparent)" } : undefined
      }
    >
      <span className="detail mono">{time(entry.at)}</span>
      <span
        className="flex items-baseline gap-2 min-w-0"
        style={{ paddingLeft: `${depth * 1.15}rem` }}
      >
        <span className="detail mono shrink-0" aria-hidden>
          └
        </span>
        <span className={`${style.chip} shrink-0`}>
          <span aria-hidden>{style.glyph}</span>
          {entry.decision}
        </span>
        <span className="truncate">
          {ACTION_LABEL[entry.action] ?? entry.action.replace(/[._]/g, " ")}
        </span>
        {text && <span className="detail truncate">{text}</span>}
      </span>
    </div>
  );
}



interface Entry {
  id: string;
  action: string;
  actor: string;
  decision: string;
  at?: string;
  details?: Record<string, unknown>;
}

interface Step {
  step_id: string;
  status?: string;
  key?: string;
  started_at?: string;
  completed_at?: string;
  /** Written when the step is claimed: which agent this hop was handed to. */
  payload?: { agent?: string } | null;
  result?: { elapsed_s?: number; tokens?: number; tools?: number } | null;
}

interface TraceData {
  run_id: string;
  trace_id?: string | null;
  status?: string;
  kind?: string;
  subject?: string;
  steps: Step[];
  entries: Entry[];
}

const DECISION_STYLE: Record<string, { chip: string; glyph: string }> = {
  blocked: { chip: "chip chip-deny", glyph: "⊘" },
  denied: { chip: "chip chip-deny", glyph: "⊘" },
  failed: { chip: "chip chip-deny", glyph: "✗" },
  escalated: { chip: "chip chip-wait", glyph: "↑" },
  awaiting_approval: { chip: "chip chip-wait", glyph: "⏸" },
  skipped: { chip: "chip chip-muted", glyph: "≡" },
  // Without this, `awaiting_human` fell through to the `done` style and the run
  // that is sitting waiting for a person was labelled with a green tick.
  awaiting_human: { chip: "chip chip-wait", glyph: "⏸" },
  accepted: { chip: "chip chip-info", glyph: "→" },
  done: { chip: "chip chip-ok", glyph: "✓" },
};

const ACTION_LABEL: Record<string, string> = {
  "event.ingested": "Event accepted",
  "artifact.uploaded": "Artifact stored",
  "guardrail.blocked": "Injected instructions blocked",
  "tool.denied": "Tool refused — outside this agent's boundary",
  "tool.unknown": "Tool refused — not in the registry",
  "tool.loop_broken": "Loop broken — same call repeating",
  "tool.external_effect": "External effect recorded before it happened",
  "budget.exceeded": "Run budget exhausted",
  "agent.step_replayed": "Step already done — skipped",
  "delegation.unknown_agent": "Plan named an agent that does not exist",
  "delegation.not_permitted": "Delegation refused — not callable by the orchestrator",
  "escalation.raised": "Escalated for a human",
  "watchdog.escalated": "Verification escalated",
  "plan.no_action": "Nothing needed doing",
  "action.awaiting_approval": "Waiting for approval",
  "action.duplicate_suppressed": "Duplicate suppressed",
  "run.finished": "Run finished",
  "redaction.model_pass": "Identifiers redacted",
};

function time(iso?: string) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function detail(entry: Entry): string {
  const d = entry.details ?? {};
  const keys = ["summary", "reason", "excerpt", "tool", "boundary", "kinds", "error", "requested"];
  return keys
    .filter((k) => d[k] != null)
    .map((k) => String(d[k]))
    .join(" · ")
    .slice(0, 300);
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className="mono text-[0.9rem] mt-0.5">{value}</p>
    </div>
  );
}

export function LiveTrace({ runId }: { runId: string }) {
  const loaded = useLive<TraceData>(`/runs/${runId}/trace`, 10_000);
  const trace = loaded.data;
  const hops = useHops(trace?.steps ?? []);

  if (loaded.status === "loading") return <LoadingScreen what={`the trail for ${runId}`} />;
  if (loaded.status === "error" || !trace) {
    return (
      <ErrorScreen what="this run's decision trail" error={loaded.error} onRetry={loaded.retry} />
    );
  }

  // Refused and escalated are different events and were being counted as one.
  // A refusal is the system saying no; an escalation is the system saying "a
  // person should decide". Reporting two escalations under a heading that reads
  // REFUSED describes a boundary violation that did not happen — on the screen
  // whose purpose is that those two things are distinguishable.
  const refused = trace.entries.filter((e) =>
    ["blocked", "denied", "failed"].includes(e.decision),
  );
  const escalated = trace.entries.filter((e) => e.decision === "escalated");
  const stopped = refused.length + escalated.length;
  const agents = agentCount(hops);

  const owned = new Map<string, Entry[]>();
  const rootEntries: Entry[] = [];
  for (const entry of trace.entries) {
    const owner = ownerOf(entry, trace.steps);
    if (!owner) rootEntries.push(entry);
    else owned.set(owner, [...(owned.get(owner) ?? []), entry]);
  }

  const longest = Math.max(1, ...trace.steps.map((s) => s.result?.elapsed_s ?? 0));

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-[var(--line-soft)]">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1 className="text-[0.98rem] font-medium">
            {stopped > 0
              ? `${trace.kind ?? "run"} — ${[
                  refused.length && `${refused.length} refused`,
                  escalated.length && `${escalated.length} escalated`,
                ]
                  .filter(Boolean)
                  .join(", ")}`
              : `${trace.kind ?? "run"} — handled without stopping`}
          </h1>
          <span className="mono text-[0.72rem] text-[var(--text-2)]">
            {trace.trace_id ? `trace ${trace.trace_id.slice(0, 16)}…` : `run ${trace.run_id}`}
          </span>
        </div>

        {hops.length > 0 && (
          <div className="mt-2.5">
            <Handoff hops={hops} compact />
          </div>
        )}
      </div>

      <div className="px-4 py-2.5 border-b border-[var(--line-soft)] grid grid-cols-2 sm:grid-cols-6 gap-4">
        <Stat label="Agents" value={String(agents)} />
        <Stat label="Hops" value={String(trace.steps.length)} />
        <Stat label="Decisions" value={String(trace.entries.length)} />
        <Stat label="Refused" value={String(refused.length)} />
        <Stat label="Escalated" value={String(escalated.length)} />
        <Stat label="Status" value={trace.status ?? "—"} />
      </div>

      <div data-density="dense" className="flex-1 min-h-0 overflow-y-auto">
        {/* Root: what happened to the run itself, outside any agent's hop. */}
        {rootEntries
          .filter((e) => (e.at ?? "") < (trace.steps[0]?.started_at ?? "\uffff"))
          .map((entry) => (
            <DecisionRow key={entry.id} entry={entry} depth={0} />
          ))}

        {trace.steps.map((step) => {
          const agent = step.payload?.agent ?? "—";
          const seconds = step.result?.elapsed_s ?? 0;
          const tint = ACTOR_TINT[agent] ?? "var(--text-2)";
          const children = owned.get(step.step_id) ?? [];

          return (
            <div key={step.step_id}>
              <div className="row grid-cols-[4.5rem_1fr_7rem_5rem]">
                <span className="detail mono">{time(step.started_at)}</span>
                <span className="flex items-center gap-2 min-w-0">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: tint }}
                    aria-hidden
                  />
                  <span className="mono truncate" style={{ color: "var(--text-0)" }}>
                    {agent}
                  </span>
                  <span
                    className={step.status === "done" ? "chip chip-ok" : "chip chip-wait"}
                  >
                    {step.status}
                  </span>
                  <span className="detail truncate" title={step.key}>
                    {step.step_id}
                  </span>
                </span>
                <Bar seconds={seconds} longest={longest} />
                <span className="detail mono text-right">
                  {step.result?.tokens ? `${step.result.tokens.toLocaleString()} tok` : ""}
                </span>
              </div>

              {children.map((entry) => (
                <DecisionRow key={entry.id} entry={entry} depth={1} />
              ))}
            </div>
          );
        })}

        {/* Root: how the run ended. */}
        {rootEntries
          .filter((e) => (e.at ?? "") >= (trace.steps[0]?.started_at ?? "\uffff"))
          .map((entry) => (
            <DecisionRow key={entry.id} entry={entry} depth={0} />
          ))}
      </div>
    </div>
  );
}
