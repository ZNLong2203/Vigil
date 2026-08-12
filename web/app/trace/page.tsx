"use client";

import { useState } from "react";
import { LiveTrace } from "@/components/LiveTrace";
import { EmptyScreen, ErrorScreen, LoadingScreen } from "@/components/Screen";
import { useLive } from "@/lib/live";

/**
 * Reasoning trace — the operator surface.
 *
 * Every run here is one the deployed fleet actually performed. There used to be
 * a committed worked example shown whenever no runs were readable; it described
 * a real scenario, but it meant this screen could present a blocked injection
 * that had never happened on this deployment, which is precisely the claim a
 * viewer has the most reason to want checked.
 */

interface RunRow {
  run_id: string;
  status?: string;
  kind?: string;
  subject?: string;
  created_at?: string;
}

export default function TracePage() {
  const [selected, setSelected] = useState<string | null>(null);
  const runs = useLive<{ runs: RunRow[] }>("/runs?limit=25", 20_000);

  if (runs.status === "loading") return <LoadingScreen what="the runs" />;
  if (runs.status === "error" || !runs.data) {
    return <ErrorScreen what="the list of runs" error={runs.error} onRetry={runs.retry} />;
  }

  if (runs.data.runs.length === 0) {
    return (
      <EmptyScreen
        title="No run has been traced yet."
        detail="This screen shows every decision one run made, in the order it made them. Send something through Intake and the run appears here while it is still working."
      />
    );
  }

  const current = selected ?? runs.data.runs[0].run_id;

  return (
    <div className="h-full flex flex-col">
      {/* Runs are listed newest first, so the one you just triggered is the one
          you land on. Selecting is how you compare a blocked run with a clean
          one, which is the comparison that shows the system working. */}
      <div
        data-density="dense"
        className="px-3 py-2 border-b border-[var(--line-soft)] flex items-center gap-2 overflow-x-auto"
      >
        <span className="eyebrow shrink-0">Runs</span>
        {runs.data.runs.slice(0, 12).map((run) => {
          const active = run.run_id === current;
          const held = run.status === "awaiting_human";
          return (
            <button
              key={run.run_id}
              type="button"
              onClick={() => setSelected(run.run_id)}
              className="chip shrink-0"
              style={{
                color: held ? "var(--amber)" : active ? "var(--azure)" : "var(--text-2)",
                background: active ? "var(--bg-2)" : "transparent",
                borderColor: active ? "currentColor" : "var(--line)",
              }}
              title={`${run.kind ?? "run"} · ${run.status ?? ""}`}
            >
              {run.run_id.slice(0, 8)}
            </button>
          );
        })}
      </div>

      <div className="flex-1 min-h-0">
        <LiveTrace runId={current} />
      </div>
    </div>
  );
}
