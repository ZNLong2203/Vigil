"use client";

import { useState } from "react";
import { FleetGraph } from "@/components/FleetGraph";
import { Callout, ScreenIntro } from "@/components/ScreenIntro";
import { SourceBadge } from "@/components/SourceBadge";
import { useLoaded } from "@/lib/live";
import { DENIED_EDGES, REGISTRY, type RegistryEntry, type VersionRecord } from "@/lib/registry";
import { DEPARTMENT_LABEL, type Department } from "@/lib/types";

/**
 * Fleet — the Agent Registry surface.
 *
 * Two things have to be answerable here, both required by the category: how
 * another department discovers and calls an agent, and what happened the last
 * time one of them tried to improve itself.
 *
 * The version history is read from the deployed eval gate when one is reachable.
 * A rejection there is the most interesting artefact the system produces — an
 * agent proposing a change to itself, the score going up, and the change being
 * refused anyway — so it is shown with the mechanism attached rather than as a
 * status word.
 */

interface LiveVersion {
  id: string;
  version?: string;
  status?: string;
  eval_score?: number;
  anti_gaming_passed?: boolean;
  reason?: string;
  refusal_rate_before?: number;
  refusal_rate_after?: number;
  diff?: string;
  per_case?: { case_id: string; passed: boolean; hard: boolean; refused: boolean }[];
}

interface LiveAgent {
  name: string;
  version: string;
  owner: string;
  summary: string;
  accepts: string;
  returns: string;
  tool_scopes: string[];
  callable_by: string[];
  eval: { suite: string; score: number; cases: number; anti_gaming_passed: boolean };
  versions: LiveVersion[];
}

function ScopeList({ label, items, empty }: { label: string; items: string[]; empty: string }) {
  return (
    <div>
      <p className="eyebrow mb-1">{label}</p>
      {items.length === 0 ? (
        <p className="text-[0.82rem] text-[var(--text-2)]">{empty}</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {items.map((s) => (
            <span key={s} className="chip chip-muted">
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** One decision by the eval gate. Rejections carry their mechanism. */
function VersionRow({
  version,
  status,
  score,
  antiGaming,
  reason,
  refusalBefore,
  refusalAfter,
  perCase,
}: {
  version: string;
  status: string;
  score?: number;
  antiGaming: boolean;
  reason?: string;
  refusalBefore?: number;
  refusalAfter?: number;
  perCase?: LiveVersion["per_case"];
}) {
  const rejected = status === "rejected";
  const hardPassed = perCase?.filter((c) => c.hard && c.passed).length;
  const hardTotal = perCase?.filter((c) => c.hard).length;

  return (
    <li
      className="px-3 py-2.5 border-b border-[var(--line-soft)] last:border-b-0"
      style={
        rejected ? { background: "color-mix(in oklab, var(--rose) 7%, transparent)" } : undefined
      }
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className="mono text-[0.85rem]">{version}</span>
        <span
          className={
            rejected
              ? "chip chip-deny"
              : status === "promoted"
                ? "chip chip-ok"
                : "chip chip-muted"
          }
        >
          {status}
        </span>
        {typeof score === "number" && (
          <span className="mono text-[0.75rem] text-[var(--text-2)]">
            eval {score.toFixed(2)}
          </span>
        )}
        <span className={antiGaming ? "chip chip-muted" : "chip chip-deny"}>
          anti-gaming {antiGaming ? "passed" : "failed"}
        </span>
      </div>

      {/* The two numbers a score cannot show. Both are why the judge exists. */}
      {(refusalBefore != null || hardTotal) && (
        <div className="mt-1.5 flex items-center gap-4 flex-wrap text-[0.75rem] text-[var(--text-2)] mono">
          {refusalBefore != null && refusalAfter != null && (
            <span
              style={
                refusalAfter > refusalBefore ? { color: "var(--rose)" } : undefined
              }
            >
              refusal on answerable {refusalBefore.toFixed(2)} → {refusalAfter.toFixed(2)}
            </span>
          )}
          {hardTotal ? (
            <span>
              hard cases {hardPassed}/{hardTotal}
            </span>
          ) : null}
        </div>
      )}

      {reason && (
        <p className="mt-2 text-[0.84rem] leading-relaxed text-[var(--text-1)]">{reason}</p>
      )}
    </li>
  );
}

function EntryDetail({ entry }: { entry: RegistryEntry }) {
  return (
    <div className="panel overflow-hidden">
      <div className="panel-head">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="mono text-[0.9rem]">{entry.name}</span>
          <span className="chip chip-info">v{entry.version}</span>
        </div>
        <span className="eyebrow shrink-0">{DEPARTMENT_LABEL[entry.owner]}</span>
      </div>

      <div className="p-4 space-y-3.5">
        <p className="text-[0.89rem] leading-relaxed text-[var(--text-1)]">{entry.summary}</p>

        <div>
          <p className="eyebrow mb-1">Capability</p>
          <p className="mono text-[0.84rem]">
            {entry.capability.input}{" "}
            <span className="text-[var(--text-2)]" aria-hidden>
              →
            </span>{" "}
            {entry.capability.output}
          </p>
        </div>

        <ScopeList label="Tool scopes" items={entry.tool_scopes} empty="none" />
        <ScopeList
          label="Callable by"
          items={entry.callable_by}
          empty="nothing — this is the entry point"
        />

        <div className="pt-3 border-t border-[var(--line-soft)] flex items-center gap-3 flex-wrap">
          <span className="chip chip-ok">
            eval {entry.eval.score.toFixed(2)} · {entry.eval.cases} cases
          </span>
          <span className="mono text-[0.75rem] text-[var(--text-2)]">{entry.eval.suite}</span>
        </div>
      </div>
    </div>
  );
}

export function FleetExplorer() {
  const [selected, setSelected] = useState<string>("meds-agent");
  const loaded = useLoaded<{ agents: LiveAgent[] }>("/registry", { agents: [] });

  const liveAgent = loaded.data.agents.find((a) => a.name === selected);
  const liveVersions = liveAgent?.versions ?? [];
  const source = loaded.source === "live" ? "live" : "fixture";

  // Scopes and capabilities come from the deployed registry when one answers.
  // The committed copy exists so the page opens without a backend, but it must
  // not be the thing on screen when the real catalogue is reachable: a UI
  // showing a stale copy of a boundary is worse than one showing none, because
  // the whole claim of this screen is that the boundaries are real.
  //
  // Layout positions stay local — where a box sits is presentation, not state.
  const local = REGISTRY.find((r) => r.name === selected) ?? REGISTRY[0];
  const entry: RegistryEntry = liveAgent
    ? {
        ...local,
        version: liveAgent.version,
        summary: liveAgent.summary,
        tool_scopes: liveAgent.tool_scopes as RegistryEntry["tool_scopes"],
        callable_by: liveAgent.callable_by as RegistryEntry["callable_by"],
        capability: { input: liveAgent.accepts, output: liveAgent.returns },
        eval: {
          suite: liveAgent.eval.suite,
          score: liveAgent.eval.score,
          cases: liveAgent.eval.cases,
          anti_gaming_passed: liveAgent.eval.anti_gaming_passed,
        },
      }
    : local;

  const graph: RegistryEntry[] = loaded.data.agents.length
    ? REGISTRY.map((r) => {
        const remote = loaded.data.agents.find((a) => a.name === r.name);
        return remote ? { ...r, version: remote.version } : r;
      })
    : REGISTRY;

  const denial = DENIED_EDGES[0];
  const history: VersionRecord[] = local.history;

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <ScreenIntro
          title="Fleet registry"
          aside={
            <>
              <SourceBadge source={source} error={loaded.error} />
              <span className="eyebrow">{graph.length} agents · 4 boundaries</span>
            </>
          }
        >
          Five agents in four departments, and what each one is allowed to touch. The
          boundaries are <em>enforced by what an agent holds</em>, not by instructions in a
          prompt — an agent is never handed a tool outside its department, and every call is
          re-checked anyway.
        </ScreenIntro>

        <div className="mb-4">
          <Callout tone="deny">
            <strong>The dashed red line is the interesting part.</strong> The benefits agent
            reached for a clinical note to fill in a form faster. It was refused, the refusal
            was recorded, and it took the legitimate route instead — a request routed through
            the orchestrator. No prompt could have widened that boundary.
          </Callout>
        </div>

        <div className="panel p-3 mb-4">
          <FleetGraph
            registry={graph}
            denied={DENIED_EDGES}
            selected={selected}
            onSelect={setSelected}
          />
        </div>

        <div className="grid lg:grid-cols-2 gap-4">
          <EntryDetail entry={entry} />

          <div className="space-y-4">
            <div className="panel overflow-hidden">
              <div className="panel-head">
                <span className="eyebrow">Version history — decided by the eval gate</span>
                <span className="eyebrow">
                  {source === "live" ? liveVersions.length : history.length} records
                </span>
              </div>
              {(source === "live" ? liveVersions : history).some(
                (v) => ("status" in v ? v.status : "") === "rejected",
              ) && (
                <div className="px-3 pt-3">
                  <Callout tone="deny">
                    <strong>This agent tried to improve itself and was refused.</strong> The
                    proposal scored <em>higher</em> than what is running, and the refusal rate
                    did not rise — every simple check said promote it. It was rejected because
                    the judge reads the instruction diff as well as the score, and the diff had
                    memorised the test.
                  </Callout>
                </div>
              )}
              <ul>
                {source === "live"
                  ? liveVersions.map((v) => (
                      <VersionRow
                        key={v.id}
                        version={v.version ?? v.id}
                        status={v.status ?? "unknown"}
                        score={v.eval_score}
                        antiGaming={v.anti_gaming_passed !== false}
                        reason={v.reason}
                        refusalBefore={v.refusal_rate_before}
                        refusalAfter={v.refusal_rate_after}
                        perCase={v.per_case}
                      />
                    ))
                  : history.map((record) => (
                      <VersionRow
                        key={record.version}
                        version={record.version}
                        status={record.status}
                        score={record.eval_score}
                        antiGaming={record.anti_gaming_passed}
                        reason={record.reason}
                      />
                    ))}
              </ul>
            </div>

            <div className="panel overflow-hidden">
              <div className="panel-head">
                <span className="eyebrow">Boundary enforcement</span>
                <span className="chip chip-deny">1 denial</span>
              </div>
              <div className="p-4">
                <p className="text-[0.88rem]">
                  <span className="mono">{denial.from}</span>{" "}
                  <span className="text-[var(--text-2)]">requested</span> {denial.resource}
                </p>
                <p className="mt-2 text-[0.86rem] leading-relaxed text-[var(--text-1)]">
                  {denial.outcome}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export type { Department };
