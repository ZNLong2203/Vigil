"use client";

import { useState } from "react";
import { DECISION_CHIP, type Trace, type TraceSpan } from "@/lib/types";

/**
 * Reasoning trace — the operator surface, and the only one that is dense.
 *
 * Density is correct here: the point of a control room is seeing the whole
 * system at once. What keeps it legible rather than loud is hierarchy — there is
 * exactly one primary read, the path the decision took down the tree, carried by
 * indentation and the duration bars. Everything an engineer needs but a reader
 * does not (span ids, token counts, cost) sits at --text-2 until you hover a row
 * or select it.
 *
 * Judges have about ten seconds to understand this screen from a video. That
 * constraint is why the headline sits above the tree in plain language.
 */

const ACTOR_TINT: Record<string, string> = {
  api: "var(--text-2)",
  guardrail: "var(--rose)",
  orchestrator: "var(--phosphor)",
  "intake-agent": "var(--phosphor)",
  "meds-agent": "var(--azure)",
  "benefits-agent": "var(--amber)",
  watchdog: "var(--violet)",
  policy: "var(--amber)",
};

function Bar({ ms, total }: { ms: number; total: number }) {
  const pct = Math.max(0.8, (ms / total) * 100);
  return (
    <div className="h-1.5 w-full rounded-full bg-[var(--bg-3)] overflow-hidden" title={`${ms} ms`}>
      <div
        className="h-full rounded-full"
        style={{ width: `${pct}%`, background: "color-mix(in oklab, var(--azure) 70%, transparent)" }}
      />
    </div>
  );
}

function Stat({ label, value, tint }: { label: string; value: string; tint?: string }) {
  return (
    <div>
      <p className="eyebrow">{label}</p>
      <p className="mono text-[0.95rem] mt-0.5" style={tint ? { color: tint } : undefined}>
        {value}
      </p>
    </div>
  );
}

export function TraceExplorer({ trace }: { trace: Trace }) {
  const [selectedId, setSelectedId] = useState<string>(
    trace.spans.find((s) => s.decision === "blocked")?.span_id ?? trace.spans[0].span_id,
  );
  const selected = trace.spans.find((s) => s.span_id === selectedId) ?? trace.spans[0];
  const slowest = Math.max(...trace.spans.map((s) => s.duration_ms));

  return (
    <div className="h-full flex flex-col">
      {/* Plain-language headline. Ten seconds of video comprehension lives here. */}
      <div className="px-4 py-3 border-b border-[var(--line-soft)] flex items-baseline gap-3 flex-wrap">
        <h1 className="text-[0.98rem] font-medium">{trace.headline}</h1>
        <span className="mono text-[0.72rem] text-[var(--text-2)]">
          trace {trace.trace_id.slice(0, 16)}…
        </span>
      </div>

      <div className="px-4 py-2.5 border-b border-[var(--line-soft)] grid grid-cols-2 sm:grid-cols-5 gap-4">
        <Stat label="Spans" value={String(trace.spans.length)} />
        <Stat label="Wall clock" value={`${(trace.total_ms / 1000).toFixed(2)} s`} />
        <Stat label="Tokens" value={trace.total_tokens.toLocaleString()} />
        <Stat label="Cost" value={`$${trace.total_cost_usd.toFixed(4)}`} />
        <Stat label="Outcome" value={trace.outcome} tint="var(--rose)" />
      </div>

      <div className="flex-1 min-h-0 grid lg:grid-cols-[1.6fr_1fr]">
        {/* ── The tree. Dense. ──────────────────────────────────────────── */}
        <div data-density="dense" className="min-h-0 overflow-y-auto border-r border-[var(--line-soft)]">
          {trace.spans.map((span) => {
            const chip = DECISION_CHIP[span.decision];
            const active = span.span_id === selectedId;
            const tint = ACTOR_TINT[span.actor] ?? "var(--text-2)";

            return (
              <button
                key={span.span_id}
                type="button"
                onClick={() => setSelectedId(span.span_id)}
                aria-current={active ? "true" : undefined}
                className="row w-full text-left grid-cols-[1fr_5rem_4.5rem_6rem]"
                style={{
                  background: active ? "var(--bg-2)" : undefined,
                  boxShadow: active ? "inset 2px 0 0 var(--azure)" : undefined,
                }}
              >
                <span
                  className="flex items-center gap-2 min-w-0"
                  style={{ paddingLeft: `${span.depth * 1.1}rem` }}
                >
                  {span.depth > 0 && (
                    <span className="detail mono shrink-0" aria-hidden>
                      └
                    </span>
                  )}
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: tint }}
                    aria-hidden
                  />
                  <span className="mono truncate">{span.name}</span>
                  <span className={`${chip.className} shrink-0`}>
                    <span aria-hidden>{chip.glyph}</span>
                    {span.decision}
                  </span>
                </span>

                <span className="detail mono text-right">
                  {span.tokens ? span.tokens.toLocaleString() : "—"}
                </span>
                <span className="detail mono text-right">{span.duration_ms}ms</span>
                <Bar ms={span.duration_ms} total={slowest} />
              </button>
            );
          })}
        </div>

        {/* ── Detail. Calm, because it is one thing at a time. ──────────── */}
        <aside data-density="calm" className="min-h-0 overflow-y-auto p-4">
          <SpanDetail span={selected} />
        </aside>
      </div>
    </div>
  );
}

function SpanDetail({ span }: { span: TraceSpan }) {
  const chip = DECISION_CHIP[span.decision];
  const tint = ACTOR_TINT[span.actor] ?? "var(--text-2)";

  return (
    <>
      <p className="eyebrow">Span</p>
      <h2 className="mono text-[1rem] mt-0.5">{span.name}</h2>

      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className={chip.className}>
          <span aria-hidden>{chip.glyph}</span>
          {span.decision}
        </span>
        <span className="chip chip-muted" style={{ color: tint }}>
          {span.actor}
        </span>
        {span.department && <span className="chip chip-muted">{span.department}</span>}
      </div>

      {span.note && (
        <p className="mt-3 text-[0.9rem] leading-relaxed text-[var(--text-1)]">{span.note}</p>
      )}

      <div className="mt-4 grid grid-cols-2 gap-3">
        <Stat label="Duration" value={`${span.duration_ms} ms`} />
        <Stat label="Model" value={span.model ?? "—"} />
        <Stat label="Tokens" value={span.tokens ? span.tokens.toLocaleString() : "—"} />
        <Stat label="Cost" value={span.cost_usd ? `$${span.cost_usd.toFixed(4)}` : "—"} />
      </div>

      <div className="mt-4 pt-3 border-t border-[var(--line-soft)]">
        <p className="eyebrow">Identifiers</p>
        <dl className="mt-1.5 space-y-1 text-[0.82rem]">
          <div className="flex gap-2">
            <dt className="text-[var(--text-2)] w-16 shrink-0">span</dt>
            <dd className="mono">{span.span_id}</dd>
          </div>
          <div className="flex gap-2">
            <dt className="text-[var(--text-2)] w-16 shrink-0">parent</dt>
            <dd className="mono">{span.parent_id ?? "root"}</dd>
          </div>
        </dl>
      </div>

      <p className="mt-4 text-[0.78rem] text-[var(--text-2)] leading-relaxed">
        These spans are OpenTelemetry, emitted by{" "}
        <span className="mono">src/vigil/telemetry.py</span>. Locally they land in Jaeger; deployed,
        in Cloud Trace. This view is a rendering of them, not a separate log.
      </p>
    </>
  );
}
