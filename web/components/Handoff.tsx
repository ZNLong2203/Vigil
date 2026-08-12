"use client";

import { DEPARTMENT_TINT, type Hop } from "@/lib/handoff";

/**
 * The chain of agents that handled one run, drawn left to right.
 *
 * This is the one picture that shows what the system actually is. Everything
 * else — the timeline, the approvals queue — is what a *single* competent
 * assistant would produce, and a viewer has no way to tell those apart from
 * five agents with separate tool scopes handing work between them. Here the
 * handoff is the subject: three named agents, three departments, and the seconds
 * and tokens each one spent, all read from the deployed run rather than drawn.
 *
 * The arrow is the claim. `orchestrator → intake-agent` means the orchestrator
 * did not do that work and could not have: it holds no business tools, only the
 * ability to look an agent up and call it. That constraint is the reason there
 * is a fleet at all, and it deserves to be visible somewhere other than a source
 * file.
 */

function fmt(n: number | null, suffix: string): string | null {
  if (n === null) return null;
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 1 })}${suffix}`;
}

export function Handoff({ hops, compact = false }: { hops: Hop[]; compact?: boolean }) {
  if (hops.length === 0) {
    return (
      <p className="text-[0.88rem] text-[var(--text-2)]">
        No agent has been handed a step in this run yet.
      </p>
    );
  }

  return (
    <ol
      className="flex items-stretch gap-1 flex-wrap"
      aria-label={`Agent handoff: ${hops.map((h) => h.agent).join(" then ")}`}
    >
      {hops.map((hop, i) => {
        const tint = hop.department ? DEPARTMENT_TINT[hop.department] : "var(--text-2)";
        const running = hop.status !== "done" && hop.status !== "failed";
        const failed = hop.status === "failed";
        const meta = [fmt(hop.seconds, "s"), fmt(hop.tokens, " tok")]
          .filter(Boolean)
          .join(" · ");

        return (
          <li key={hop.step_id} className="flex items-stretch gap-1 min-w-0">
            {i > 0 && (
              <span
                className="self-center mono text-[var(--text-2)] px-0.5 shrink-0"
                aria-hidden
                title="handed the work to"
              >
                →
              </span>
            )}

            <div
              className="rounded-md border px-2.5 py-1.5 min-w-0"
              style={{
                borderColor: failed
                  ? "var(--rose)"
                  : `color-mix(in oklab, ${tint} 45%, transparent)`,
                background: `color-mix(in oklab, ${tint} 7%, transparent)`,
              }}
              title={`${hop.agent} — ${hop.role}${hop.tools !== null ? ` · ${hop.tools} tool call${hop.tools === 1 ? "" : "s"}` : ""}`}
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span
                  className="w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: tint }}
                  aria-hidden
                />
                <span className="mono text-[0.8rem] truncate" style={{ color: "var(--text-0)" }}>
                  {hop.agent}
                </span>
                {running && (
                  <span className="live-dot shrink-0" style={{ width: "0.4rem", height: "0.4rem" }} aria-label="running" />
                )}
              </div>

              {!compact && (
                <p className="text-[0.76rem] mt-0.5" style={{ color: "var(--text-2)" }}>
                  {hop.role}
                </p>
              )}
              {meta && (
                <p className="mono text-[0.7rem] mt-0.5" style={{ color: "var(--text-2)" }}>
                  {meta}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
