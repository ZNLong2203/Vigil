"use client";

import { ScreenIntro } from "@/components/ScreenIntro";
import { SourceBadge } from "@/components/SourceBadge";
import { auditToTimeline, useLoaded } from "@/lib/live";
import { TIMELINE } from "@/lib/mock";
import { DECISION_CHIP, DEPARTMENT_LABEL, type TimelineEvent } from "@/lib/types";

/**
 * Timeline — a caregiver surface, therefore calm density.
 *
 * The primary read is "what happened, and did it need me?". Everything else —
 * confidence, provenance, the agent that acted — is secondary and recedes until
 * the row is hovered.
 *
 * Live where a backend answers, committed sample data where none does, and the
 * badge in the header says which. Polls while open, because a fleet run takes
 * about a minute and a frozen screen reads as a broken one.
 */

const DAY0 = new Date("2026-08-03T09:00:00Z").getTime();
const weekOf = (iso: string) => Math.floor((new Date(iso).getTime() - DAY0) / (7 * 864e5)) + 1;

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

function Event({ event, conflictTarget }: { event: TimelineEvent; conflictTarget?: TimelineEvent }) {
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

        {conflictTarget && (
          <p
            className="mt-2 text-[0.85rem] px-3 py-2 rounded-md border"
            style={{
              borderColor: "color-mix(in oklab, var(--amber) 35%, transparent)",
              background: "color-mix(in oklab, var(--amber) 7%, transparent)",
              color: "var(--text-1)",
            }}
          >
            Contradicts <strong className="text-[var(--text-0)]">{conflictTarget.title}</strong> on{" "}
            {formatDay(conflictTarget.at)}. Both sources are kept; neither is overwritten.
          </p>
        )}

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

export default function TimelinePage() {
  const loaded = useLoaded<{ entries: Parameters<typeof auditToTimeline>[0] }>(
    "/audit?limit=200",
    { entries: [] },
    15_000,
  );

  const live = loaded.source === "live" ? auditToTimeline(loaded.data.entries) : [];
  const events = live.length > 0 ? live : TIMELINE;
  const source = live.length > 0 ? "live" : "fixture";

  const byId = new Map(events.map((e) => [e.id, e]));
  const weeks = [...new Set(events.map((e) => weekOf(e.at)))].sort((a, b) => a - b);
  const attention = events.filter(
    (e) => e.decision === "awaiting_approval" || e.decision === "escalated",
  ).length;

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-6">
        <ScreenIntro
          title={source === "live" ? "What the fleet has done" : "Three weeks of care"}
          aside={
            <>
              <SourceBadge source={source} error={loaded.error} />
              <span className="eyebrow">{events.length} events</span>
            </>
          }
        >
          {attention > 0 ? (
            <>
              Everything the agents did, oldest first.{" "}
              <em>{attention} of these need you</em> — they are the amber rows. The rest was
              handled without asking.
            </>
          ) : (
            <>
              Everything the agents did, oldest first. <em>Nothing needs you right now</em> —
              every item here was handled without asking.
            </>
          )}
        </ScreenIntro>

        {weeks.map((week) => (
          <section key={week} className="mb-5">
            <div className="flex items-center gap-3 mb-2">
              <span className="eyebrow">
                {source === "live" ? formatDay(events.find((e) => weekOf(e.at) === week)!.at) : `Week ${week}`}
              </span>
              <span className="h-px flex-1 bg-[var(--line-soft)]" />
            </div>

            <div className="panel overflow-hidden">
              {events
                .filter((e) => weekOf(e.at) === week)
                .map((event) => (
                  <Event
                    key={event.id}
                    event={event}
                    conflictTarget={
                      event.conflicts_with ? byId.get(event.conflicts_with) : undefined
                    }
                  />
                ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
