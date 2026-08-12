"use client";

import { useMemo, useState } from "react";
import { ScreenIntro } from "@/components/ScreenIntro";
import { EmptyScreen, ErrorScreen, LoadingScreen } from "@/components/Screen";
import { auditToTimeline, useLive } from "@/lib/live";
import { DECISION_CHIP, DEPARTMENT_LABEL, type TimelineEvent } from "@/lib/types";

/**
 * Timeline — a caregiver surface, therefore calm density.
 *
 * The primary read is "what happened, and did it need me?". Everything else —
 * confidence, provenance, the agent that acted — is secondary and recedes until
 * the row is opened.
 *
 * One row per run, not per audit entry, and that is the whole design. Rendering
 * the trail directly produced seventy rows for sixteen pieces of work, because
 * every run contributes an "Event accepted" and a "Run finished" whatever else
 * it does — forty-three per cent of the screen was bookkeeping. Paging through
 * that would have been paging through noise; the list was not too long, it was
 * too granular. A run is the unit a person actually thinks in: this document
 * arrived, this is what came of it, and here is the detail if you want it.
 */

// Weeks were the grouping when the screen showed a three-week authored story.
// Real runs arrive in bursts on the days someone uses the system, so days are
// the unit that produces headings a person recognises.

function formatDay(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

function Event({ event }: { event: TimelineEvent }) {
  const chip = DECISION_CHIP[event.decision];
  const needsAttention =
    event.decision === "awaiting_approval" || event.decision === "escalated";
  const blocked = event.decision === "blocked" || event.decision === "denied";

  return (
    <article
      className={`dept-${event.department} flex gap-3 px-4 py-4 border-b border-[var(--line-soft)] last:border-b-0`}
      style={
        needsAttention
          ? { background: "color-mix(in oklab, var(--amber) 5%, transparent)" }
          : blocked
            ? { background: "color-mix(in oklab, var(--rose) 5%, transparent)" }
            : undefined
      }
    >
      <span className="dept-bar" aria-hidden />

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2.5 flex-wrap">
          <h3 className="text-[0.98rem] font-medium">{event.title}</h3>
          <span className={chip.className}>
            <span aria-hidden>{chip.glyph}</span>
            {event.decision.replace("_", " ")}
          </span>
        </div>

        {event.detail && (
          <p className="mt-1.5 text-[0.9rem] leading-relaxed text-[var(--text-1)] break-words">
            {event.detail}
          </p>
        )}

        {/* A "contradicts an earlier source" callout lived here, driven by a
            `conflicts_with` field. Nothing on the wire sets it — the mapping in
            lib/live.ts never populated it and the backend never emitted it — so
            it could only ever have rendered from authored data. Removed with
            the rest of it rather than left as a branch that never runs. */}

        <div className="mt-2 flex items-center gap-3 flex-wrap text-[var(--text-2)] text-[0.78rem]">
          <span className="mono">{formatTime(event.at)}</span>
          <span>{DEPARTMENT_LABEL[event.department]}</span>
          <span className="mono">{event.actor}</span>
          {typeof event.confidence === "number" && (
            <span className="mono" title="Model confidence in this extraction">
              conf {event.confidence.toFixed(2)}
            </span>
          )}
          {event.source_uri && (
            <span className="mono truncate max-w-[22rem]" title={event.source_uri}>
              ↳ {event.source_uri.split("/").pop()}
            </span>
          )}
        </div>
      </div>
    </article>
  );
}

interface RunGroup {
  run_id: string;
  at: string;
  events: TimelineEvent[];
  needsYou: boolean;
  blocked: boolean;
  /** Set on the run.finished entry: how many agents, how many tokens. */
  agents?: number;
  tokens?: number;
}

/** The two entries every run emits whatever it does. Kept inside the expanded
 *  detail, never shown as the headline — "Run finished" is not news. */
const BOOKKEEPING = new Set(["Document received", "Run finished"]);

function headline(group: RunGroup): TimelineEvent {
  const notable = group.events.find((e) => !BOOKKEEPING.has(e.title));
  return notable ?? group.events[0];
}

function RunRow({ group, defaultOpen }: { group: RunGroup; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const lead = headline(group);
  const chip = DECISION_CHIP[lead.decision];

  return (
    <div
      className={`dept-${lead.department} border-b border-[var(--line-soft)] last:border-b-0`}
      style={
        group.needsYou
          ? { background: "color-mix(in oklab, var(--amber) 5%, transparent)" }
          : group.blocked
            ? { background: "color-mix(in oklab, var(--rose) 5%, transparent)" }
            : undefined
      }
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full text-left flex gap-3 px-4 py-3.5 hover:bg-[var(--bg-2)] transition-colors"
      >
        <span className="dept-bar" aria-hidden />

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2.5 flex-wrap">
            <h3 className="text-[0.98rem] font-medium">{lead.title}</h3>
            <span className={chip.className}>
              <span aria-hidden>{chip.glyph}</span>
              {lead.decision.replace("_", " ")}
            </span>
          </div>

          {lead.detail && (
            <p className="mt-1 text-[0.9rem] leading-relaxed text-[var(--text-1)] line-clamp-2">
              {lead.detail}
            </p>
          )}

          <div className="mt-1.5 flex items-center gap-3 flex-wrap text-[var(--text-2)] text-[0.78rem]">
            <span className="mono">{formatTime(group.at)}</span>
            <span>{DEPARTMENT_LABEL[lead.department]}</span>
            {group.agents ? <span className="mono">{group.agents} agents</span> : null}
            {group.tokens ? (
              <span className="mono">{group.tokens.toLocaleString()} tok</span>
            ) : null}
            <span className="mono">
              {group.events.length} decision{group.events.length === 1 ? "" : "s"}
            </span>
          </div>
        </div>

        <span className="mono text-[var(--text-2)] shrink-0 self-center" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>

      {open && (
        <div className="pl-4 pb-2">
          {group.events.map((event) => (
            <Event key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function TimelinePage() {
  const audit = useLive<{ entries: Parameters<typeof auditToTimeline>[0] }>(
    "/audit?limit=300",
    15_000,
  );
  const [onlyMine, setOnlyMine] = useState(false);

  const events = useMemo(
    () => (audit.data ? auditToTimeline(audit.data.entries) : []),
    [audit.data],
  );

  // Grouped newest-first: a caregiver opening this wants the thing that just
  // happened, not the oldest surviving audit row.
  const groups = useMemo(() => {
    const byRun = new Map<string, RunGroup>();
    events.forEach((event, index) => {
      const key = event.run_id ?? `single-${event.id}-${index}`;
      const existing = byRun.get(key);
      const needsYou = event.decision === "awaiting_approval" || event.decision === "escalated";
      const blocked = event.decision === "blocked" || event.decision === "denied";

      if (existing) {
        existing.events.push(event);
        existing.needsYou ||= needsYou;
        existing.blocked ||= blocked;
      } else {
        byRun.set(key, { run_id: key, at: event.at, events: [event], needsYou, blocked });
      }
    });

    const raw = audit.data?.entries ?? [];
    for (const group of byRun.values()) {
      const finished = raw.find(
        (e) =>
          e.action === "run.finished" &&
          (e.details as { run_id?: string } | undefined)?.run_id === group.run_id,
      );
      const details = finished?.details as { agents?: number; tokens?: number } | undefined;
      group.agents = details?.agents;
      group.tokens = details?.tokens;
      // The run's own clock starts at its first entry.
      group.at = group.events[0].at;
    }

    return [...byRun.values()].sort((a, b) => b.at.localeCompare(a.at));
  }, [events, audit.data]);

  if (audit.status === "loading") return <LoadingScreen what="the audit trail" />;
  if (audit.status === "error" || !audit.data) {
    return <ErrorScreen what="the audit trail" error={audit.error} onRetry={audit.retry} />;
  }

  if (groups.length === 0) {
    return (
      <EmptyScreen
        title="The fleet has not done anything yet."
        detail="Every entry on this screen is a decision some agent recorded. Send a document through Intake and this fills in as the run proceeds."
      />
    );
  }

  const attention = groups.filter((g) => g.needsYou).length;
  const shown = onlyMine ? groups.filter((g) => g.needsYou) : groups;
  const days = [...new Set(shown.map((g) => formatDay(g.at)))];

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <ScreenIntro
          title="What the fleet has done"
          aside={
            <>
              {audit.error && (
                <span className="chip chip-wait" title={audit.error}>
                  reconnecting
                </span>
              )}
              <span className="eyebrow">
                {groups.length} runs · {events.length} decisions
              </span>
            </>
          }
        >
          {attention > 0 ? (
            <>
              One row per piece of work, newest first. <em>{attention} need you</em> — the amber
              rows. Open any row to see every decision the agents took inside it.
            </>
          ) : (
            <>
              One row per piece of work, newest first. <em>Nothing needs you right now</em> —
              every run here finished on its own. Open any row to see how.
            </>
          )}
        </ScreenIntro>

        {attention > 0 && (
          <div className="flex items-center gap-2 mb-3">
            <button
              type="button"
              className="chip"
              onClick={() => setOnlyMine(false)}
              style={
                !onlyMine
                  ? { borderColor: "var(--azure)", color: "var(--azure)" }
                  : { color: "var(--text-2)" }
              }
            >
              Everything ({groups.length})
            </button>
            <button
              type="button"
              className="chip"
              onClick={() => setOnlyMine(true)}
              style={
                onlyMine
                  ? { borderColor: "var(--amber)", color: "var(--amber)" }
                  : { color: "var(--text-2)" }
              }
            >
              Needs you ({attention})
            </button>
          </div>
        )}

        {days.map((day) => (
          <section key={day} className="mb-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="eyebrow">{day}</span>
              <span className="h-px flex-1 bg-[var(--line-soft)]" />
            </div>

            <div className="panel overflow-hidden">
              {shown
                .filter((g) => formatDay(g.at) === day)
                .map((group) => (
                  <RunRow
                    key={group.run_id}
                    group={group}
                    /* The one that needs you opens itself; everything else waits
                       to be asked. */
                    defaultOpen={group.needsYou && attention <= 3}
                  />
                ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
