"use client";

import { useState } from "react";
import { FleetGraph } from "@/components/FleetGraph";
import { DENIED_EDGES, REGISTRY, type RegistryEntry, type VersionRecord } from "@/lib/registry";
import { DEPARTMENT_LABEL } from "@/lib/types";

/**
 * Fleet — the Agent Registry surface.
 *
 * Two things have to be answerable here, both required by the category:
 * how another department discovers and calls an agent, and what happened the
 * last time one of them tried to improve itself.
 */

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

function VersionRow({ record }: { record: VersionRecord }) {
  const rejected = record.status === "rejected";

  return (
    <li
      className="px-3 py-2.5 border-b border-[var(--line-soft)] last:border-b-0"
      style={
        rejected
          ? { background: "color-mix(in oklab, var(--rose) 7%, transparent)" }
          : undefined
      }
    >
      <div className="flex items-center gap-2 flex-wrap">
        <span className="mono text-[0.85rem]">{record.version}</span>
        <span
          className={
            rejected ? "chip chip-deny" : record.status === "promoted" ? "chip chip-ok" : "chip chip-muted"
          }
        >
          {record.status}
        </span>
        <span className="mono text-[0.75rem] text-[var(--text-2)]">
          eval {record.eval_score.toFixed(2)}
        </span>
        <span className={record.anti_gaming_passed ? "chip chip-muted" : "chip chip-deny"}>
          anti-gaming {record.anti_gaming_passed ? "passed" : "failed"}
        </span>
      </div>

      {record.reason && (
        <p className="mt-2 text-[0.84rem] leading-relaxed text-[var(--text-1)]">{record.reason}</p>
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
          <span className="mono text-[0.75rem] text-[var(--text-2)]">
            promoted {new Date(entry.promoted_at).toLocaleDateString("en-GB")}
          </span>
        </div>
      </div>
    </div>
  );
}

export function FleetExplorer() {
  const [selected, setSelected] = useState<string>("meds-agent");
  const entry = REGISTRY.find((r) => r.name === selected) ?? REGISTRY[0];
  const denial = DENIED_EDGES[0];

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="text-lg font-medium">Fleet registry</h1>
          <span className="eyebrow">{REGISTRY.length} agents · 4 boundaries</span>
        </div>
        <p className="text-[var(--text-1)] text-[0.9rem] mt-1 mb-4">
          What one department has to read before it may call something another department owns.
          Boundaries are enforced by Agent Identity, not by instructions in a prompt.
        </p>

        <div className="panel p-3 mb-4">
          <FleetGraph
            registry={REGISTRY}
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
                <span className="eyebrow">Version history</span>
                <span className="eyebrow">{entry.history.length} records</span>
              </div>
              <ul>
                {entry.history.map((record) => (
                  <VersionRow key={record.version} record={record} />
                ))}
              </ul>
            </div>

            {/* The refused read, in words, next to the dashed edge that shows it. */}
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
                <p className="mono text-[0.72rem] text-[var(--text-2)] mt-2">
                  {new Date(denial.at).toLocaleString("en-GB")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
