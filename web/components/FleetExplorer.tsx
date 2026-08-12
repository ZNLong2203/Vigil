"use client";

import { useState } from "react";
import { FleetGraph } from "@/components/FleetGraph";
import { Callout, ScreenIntro } from "@/components/ScreenIntro";
import { ErrorScreen, LoadingScreen } from "@/components/Screen";
import {
  DEPARTMENT_BANDS,
  useBoundaries,
  useRegistry,
  useRuntimeDenials,
  type DeniedEdge,
  type RegistryEntry,
} from "@/lib/registry";
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
  const registry = useRegistry();
  const runtimeDenials = useRuntimeDenials();

  if (registry.status === "loading") return <LoadingScreen what="the agent registry" />;
  if (registry.status === "error" || registry.entries.length === 0) {
    return (
      <ErrorScreen
        what="the agent registry"
        error={registry.error}
        onRetry={registry.retry}
      />
    );
  }

  const graph = registry.entries;
  const entry = graph.find((r) => r.name === selected) ?? graph[0];
  const versions = entry.versions;

  // What the selected agent cannot reach. Shown for one agent at a time because
  // every agent is outside most departments — drawing all of them at once is a
  // diagram of the obvious, while one selected agent answers the question a
  // reader actually has: what is this one kept away from?
  const denied = useBoundaries(entry, registry.scopeOwners);

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <ScreenIntro
          title="Fleet registry"
          aside={
            <>
              {registry.error && (
                <span className="chip chip-wait" title={registry.error}>
                  reconnecting
                </span>
              )}
              <span className="eyebrow">
                {graph.length} agents · {DEPARTMENT_BANDS.length} boundaries
              </span>
            </>
          }
        >
          Five agents in four departments, and what each one is allowed to touch. The
          boundaries are <em>enforced by what an agent holds</em>, not by instructions in a
          prompt — an agent is never handed a tool outside its department, and every call is
          re-checked anyway.
        </ScreenIntro>

        {denied.length > 0 && (
          <div className="mb-4">
            <Callout tone="deny">
              <strong>The dashed red lines are the interesting part.</strong> They are the
              departments <span className="mono">{entry.name}</span> cannot reach. It is not
              told to stay out — it is never handed a tool that would take it there, so there
              is no declaration in its context to call. Selecting a different agent redraws
              the boundaries around that one.
            </Callout>
          </div>
        )}

        <div className="panel p-3 mb-4">
          <FleetGraph
            registry={graph}
            denied={denied}
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
                <span className="eyebrow">{versions.length} records</span>
              </div>

              {versions.some((v) => v.status === "rejected") && (
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

              {versions.length === 0 ? (
                <p className="p-4 text-[0.86rem] text-[var(--text-2)]">
                  No agent has proposed a change to itself yet. When one does, the gate&rsquo;s
                  decision — and its reasoning — appears here.
                </p>
              ) : (
                <ul>
                  {versions.map((v) => (
                    <VersionRow
                      key={v.id}
                      version={v.version ?? v.id}
                      status={v.status ?? "unknown"}
                      score={v.eval_score}
                      antiGaming={v.anti_gaming_passed !== false}
                      reason={v.reason}
                      refusalBefore={v.refusal_rate_before}
                      refusalAfter={v.refusal_rate_after}
                      perCase={
                        v.per_case as
                          | { case_id: string; passed: boolean; hard: boolean; refused: boolean }[]
                          | undefined
                      }
                    />
                  ))}
                </ul>
              )}
            </div>

            <div className="panel overflow-hidden">
              <div className="panel-head">
                <span className="eyebrow">Boundary enforcement</span>
                <span className="chip chip-muted">{runtimeDenials.length} refused at call time</span>
              </div>
              <div className="p-4 space-y-3">
                <div>
                  <p className="eyebrow mb-1.5">Layer 1 — assembly</p>
                  <p className="text-[0.86rem] leading-relaxed text-[var(--text-1)]">
                    <span className="mono">{entry.name}</span> holds{" "}
                    {entry.tool_scopes.length} scope
                    {entry.tool_scopes.length === 1 ? "" : "s"}, so its belt is{" "}
                    {entry.tools?.length ?? 0} tool
                    {(entry.tools?.length ?? 0) === 1 ? "" : "s"}
                    {entry.tools?.length ? ": " : "."}
                    {entry.tools?.length ? <span className="mono">{entry.tools.join(", ")}</span> : null}{" "}
                    Everything else in the system is absent from its context entirely.
                  </p>
                </div>

                <div>
                  <p className="eyebrow mb-1.5">Layer 2 — every call, re-checked</p>
                  <p className="text-[0.86rem] leading-relaxed text-[var(--text-1)]">
                    {runtimeDenials.length === 0 ? (
                      <>
                        Nothing has been refused at call time, which is the expected result:
                        layer 2 only fires if layer 1 was wired wrong. It exists because the
                        first layer is a property of our wiring, and wiring changes.
                      </>
                    ) : (
                      <>
                        {runtimeDenials.length} call{runtimeDenials.length === 1 ? " was" : "s were"}{" "}
                        stopped before running.
                      </>
                    )}
                  </p>
                  {runtimeDenials.length > 0 && (
                    <ul className="mt-2 space-y-2">
                      {runtimeDenials.map((d: DeniedEdge, i: number) => (
                        <li key={`${d.from}-${i}`} className="text-[0.84rem]">
                          <span className="mono">{d.from}</span>{" "}
                          <span className="text-[var(--text-2)]">tried</span>{" "}
                          <span className="mono">{d.resource}</span>
                          <p className="text-[var(--text-1)] leading-relaxed">{d.outcome}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export type { Department };
