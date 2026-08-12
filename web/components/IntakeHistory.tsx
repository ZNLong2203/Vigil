"use client";

import { useLive } from "@/lib/live";

/**
 * Everything the fleet has already read, paired with what it understood.
 *
 * This is the argument of the Intake screen and until now it could not be made
 * from real data. The checkpoint recorded what a hop *cost* — tokens, seconds,
 * tool calls — and discarded what it *concluded*, so the structured reading of a
 * crooked photograph existed for the length of one run and then was gone. The
 * screen filled the hole with hand-written worked examples, which made a missing
 * capability look like a presentation choice.
 *
 * Now the agent's output is stored on the checkpoint, so each row here is a real
 * artifact on the left and the real claims extracted from it on the right, with
 * the confidence the agent assigned to each. Confidence is the interesting
 * column: a system that reads a blurry label and says 0.55 is telling you
 * something a system that says 0.98 about everything cannot.
 */

interface Step {
  step_id: string;
  payload?: { agent?: string } | null;
  result?: {
    elapsed_s?: number;
    tokens?: number;
    output?: {
      kind?: string;
      summary?: string;
      language?: string | null;
      needs_human?: boolean;
      claims?: { field: string; value: string; confidence?: number; provenance?: unknown }[];
    } | null;
  } | null;
}

interface TraceData {
  run_id: string;
  kind?: string;
  status?: string;
  created_at?: string;
  steps: Step[];
}

const KIND_GLYPH: Record<string, string> = {
  photo: "▣",
  voice_note: "◍",
  document: "▤",
  manual: "✎",
  webhook: "⇄",
};

function confidenceTint(c: number): string {
  if (c >= 0.85) return "var(--phosphor)";
  if (c >= 0.6) return "var(--amber)";
  return "var(--rose)";
}

function filename(uri?: string | null): string | null {
  if (!uri) return null;
  return uri.split("/").pop() ?? null;
}

export function IntakeRun({ runId, sourceUri }: { runId: string; sourceUri?: string | null }) {
  const trace = useLive<TraceData>(`/runs/${runId}/trace`, 0);
  const data = trace.data;

  // The reading belongs to whichever agent was handed the artifact. Looked up by
  // the agent recorded on the hop rather than by step id, because `delegate-0-…`
  // is a storage key and the agent that reads an artifact is not always the same
  // one.
  const hop = data?.steps.find(
    (s) => s.result?.output?.claims && s.payload?.agent && s.step_id.startsWith("delegate-"),
  );
  const output = hop?.result?.output;

  if (trace.status === "loading") {
    return <div className="panel p-4 skeleton h-20" aria-label="Reading this run" />;
  }
  if (!output) return null;

  const claims = output.claims ?? [];
  const name = filename(sourceUri);

  return (
    <article className="panel overflow-hidden">
      <div className="panel-head">
        <div className="flex items-center gap-2.5 min-w-0">
          <span aria-hidden style={{ color: "var(--text-2)" }}>
            {KIND_GLYPH[data?.kind ?? ""] ?? "▤"}
          </span>
          <span className="mono text-[0.82rem] truncate">{name ?? data?.kind ?? "event"}</span>
          {output.language && <span className="chip chip-muted">{output.language}</span>}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {output.needs_human && <span className="chip chip-wait">too degraded to trust</span>}
          <span className="eyebrow">
            {hop?.result?.elapsed_s ? `${hop.result.elapsed_s.toFixed(1)}s` : ""}
          </span>
        </div>
      </div>

      <div className="grid md:grid-cols-[1fr_1.4fr]">
        {/* What arrived. */}
        <div className="p-4 md:border-r border-[var(--line-soft)]">
          <p className="eyebrow mb-1.5">What arrived</p>
          <p className="text-[0.9rem] leading-relaxed text-[var(--text-1)]">{output.summary}</p>
          {name && (
            <p className="mono text-[0.72rem] mt-2 text-[var(--text-2)] break-all">{name}</p>
          )}
        </div>

        {/* What was understood — the half that used to be invented. */}
        <div className="p-4">
          <div className="flex items-baseline justify-between gap-2 mb-1.5">
            <p className="eyebrow">What was understood</p>
            <span className="eyebrow">
              {claims.length} claim{claims.length === 1 ? "" : "s"}
            </span>
          </div>

          {claims.length === 0 ? (
            <p className="text-[0.86rem] text-[var(--text-2)]">
              Nothing could be extracted with enough confidence to record.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {claims.map((claim, i) => {
                const c = typeof claim.confidence === "number" ? claim.confidence : null;
                return (
                  <li
                    key={`${claim.field}-${i}`}
                    className="grid grid-cols-[7.5rem_1fr_3rem] gap-2 items-baseline text-[0.86rem]"
                  >
                    <span className="mono text-[0.76rem] text-[var(--text-2)] truncate">
                      {claim.field}
                    </span>
                    <span className="text-[var(--text-1)] break-words">{claim.value}</span>
                    {c !== null && (
                      <span
                        className="mono text-[0.74rem] text-right"
                        style={{ color: confidenceTint(c) }}
                        title="How sure the agent is, judged on the evidence it had"
                      >
                        {c.toFixed(2)}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </article>
  );
}
