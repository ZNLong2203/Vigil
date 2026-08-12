"use client";

import { REGISTRY } from "@/lib/registry";
import { useLoaded } from "@/lib/live";

/**
 * The fleet, always visible.
 *
 * An earlier version rendered a per-agent state — `intake-agent: working`,
 * `benefits-agent: waiting` — from a hand-written array in the mock module. It
 * looked like the most informative thing on the screen and it was the only
 * dishonest one: those states were invented, never changed, and were on display
 * beside a badge whose entire job is to tell the viewer which data is real. A
 * fabricated status bar undoes the credibility that badge is there to build.
 *
 * The registry is a real deployment fact — these five agents exist, in these
 * departments, at these versions — so the names stay. What is gone is the claim
 * about what each one is doing right now, which nothing on the wire supports:
 * a run document carries a status, not a current agent. In its place is one
 * aggregate drawn from live runs, and when there are no live runs it says so
 * rather than guessing.
 */

const DEPT_LABEL: Record<string, string> = {
  family: "family",
  clinical: "clinical",
  benefits: "benefits",
  audit: "audit",
};

interface RunRow {
  status?: string;
}

export function StatusBar() {
  const runs = useLoaded<{ runs: RunRow[] }>("/runs?limit=20", { runs: [] }, 20_000);
  const live = runs.source === "live";
  const rows = live ? runs.data.runs : [];

  const running = rows.filter((r) => r.status === "running").length;
  const waiting = rows.filter((r) => r.status === "awaiting_human").length;

  const state = !live
    ? { chip: "chip chip-muted", text: "no API configured" }
    : running
      ? { chip: "chip chip-ok", text: `${running} run${running > 1 ? "s" : ""} in flight` }
      : waiting
        ? { chip: "chip chip-wait", text: `${waiting} waiting on a human` }
        : { chip: "chip chip-muted", text: "fleet idle" };

  return (
    <footer
      data-density="dense"
      className="shrink-0 border-t border-[var(--line-soft)] px-4 py-1.5 flex items-center gap-3 flex-wrap"
    >
      <span className="eyebrow">Fleet</span>
      {REGISTRY.map((agent) => (
        <span
          key={agent.name}
          className={`chip chip-muted dept-${agent.owner}`}
          title={`${agent.name} · ${DEPT_LABEL[agent.owner]} · v${agent.version}`}
        >
          {agent.name}
        </span>
      ))}
      <span className={state.chip} title="Read from the deployed API">
        {state.text}
      </span>
      <span className="ml-auto eyebrow">gemini-3.5-flash · cloud run · us-central1</span>
    </footer>
  );
}
