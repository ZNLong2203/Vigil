"use client";

import { useLoaded } from "@/lib/live";

/**
 * One run's reasoning chain, read from the deployed audit trail.
 *
 * Dense, because the point of an operator surface is seeing the whole run at
 * once. What keeps it legible is that there is one primary read — the order
 * decisions were taken in — and everything an engineer needs but a reader does
 * not (step ids, keys, timings) sits at --text-2 until the row is hovered.
 *
 * Refusals are the rows worth finding, so they are the rows that carry colour.
 * A trace where nothing was refused should look uneventful; that is information
 * too.
 */

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
  result?: Record<string, unknown>;
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
  const loaded = useLoaded<TraceData | null>(`/runs/${runId}/trace`, null, 10_000);
  const trace = loaded.data;

  if (!trace) {
    return (
      <div data-density="calm" className="p-6">
        <p className="text-[var(--text-1)] text-[0.9rem]">Reading the trail for {runId}…</p>
      </div>
    );
  }

  const refusals = trace.entries.filter((e) =>
    ["blocked", "denied", "escalated", "failed"].includes(e.decision),
  );

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-[var(--line-soft)]">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1 className="text-[0.98rem] font-medium">
            {refusals.length > 0
              ? `${trace.kind ?? "run"} — ${refusals.length} refused, ${trace.status}`
              : `${trace.kind ?? "run"} — handled without stopping`}
          </h1>
          <span className="mono text-[0.72rem] text-[var(--text-2)]">
            {trace.trace_id ? `trace ${trace.trace_id.slice(0, 16)}…` : `run ${trace.run_id}`}
          </span>
        </div>
      </div>

      <div className="px-4 py-2.5 border-b border-[var(--line-soft)] grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Stat label="Steps" value={String(trace.steps.length)} />
        <Stat label="Decisions" value={String(trace.entries.length)} />
        <Stat label="Refused" value={String(refusals.length)} />
        <Stat label="Status" value={trace.status ?? "—"} />
      </div>

      <div data-density="dense" className="flex-1 min-h-0 overflow-y-auto">
        {trace.entries.map((entry) => {
          const style = DECISION_STYLE[entry.decision] ?? DECISION_STYLE.done;
          const notable = ["blocked", "denied", "escalated", "failed"].includes(entry.decision);
          const text = detail(entry);

          return (
            <div
              key={entry.id}
              className="row grid-cols-[4.5rem_7rem_1fr]"
              style={
                notable
                  ? { background: "color-mix(in oklab, var(--rose) 5%, transparent)" }
                  : undefined
              }
            >
              <span className="detail mono">{time(entry.at)}</span>
              <span className="mono truncate" style={{ color: "var(--text-1)" }}>
                {entry.actor}
              </span>
              <span className="flex items-baseline gap-2 min-w-0">
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
        })}

        {trace.steps.length > 0 && (
          <>
            <div className="px-3 py-2 border-y border-[var(--line-soft)]">
              <span className="eyebrow">Checkpoints — one idempotency claim per step</span>
            </div>
            {trace.steps.map((step) => (
              <div key={step.step_id} className="row grid-cols-[1fr_6rem_10rem]">
                <span className="mono truncate">{step.step_id}</span>
                <span
                  className={step.status === "done" ? "chip chip-ok" : "chip chip-wait"}
                  style={{ justifySelf: "start" }}
                >
                  {step.status}
                </span>
                <span className="detail mono truncate" title={step.key}>
                  {step.key ? `key ${step.key.slice(0, 12)}…` : ""}
                </span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
