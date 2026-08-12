"use client";

import { useState } from "react";
import { TraceExplorer } from "@/components/TraceExplorer";
import { LiveTrace } from "@/components/LiveTrace";
import { SourceBadge } from "@/components/SourceBadge";
import { useLoaded } from "@/lib/live";
import { TRACE } from "@/lib/mock";

/**
 * Reasoning trace — the operator surface.
 *
 * Live where there are runs to show, and the committed sample otherwise. The
 * sample is not a stand-in for a missing feature: it is a worked example of the
 * one run worth studying, the document whose injection was blocked, kept so the
 * screen means something to a reader with no backend attached.
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
  const runs = useLoaded<{ runs: RunRow[] }>("/runs?limit=25", { runs: [] }, 20_000);
  const live = runs.source === "live" && runs.data.runs.length > 0;

  if (!live) {
    return (
      <div className="h-full flex flex-col">
        <div className="px-4 py-2 border-b border-[var(--line-soft)] flex items-center gap-2">
          <SourceBadge source="fixture" error={runs.error} />
          <span className="eyebrow">worked example — no runs to read</span>
        </div>
        <div className="flex-1 min-h-0">
          <TraceExplorer trace={TRACE} />
        </div>
      </div>
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
        <SourceBadge source="live" />
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
