"use client";

import Link from "next/link";
import { ErrorScreen, LoadingScreen } from "@/components/Screen";
import { useLive } from "@/lib/live";
import { Handoff } from "@/components/Handoff";
import { agentCount, useHops } from "@/lib/handoff";

/**
 * The landing screen, which did not exist and should have from the start.
 *
 * Someone opening this link has no idea what Vigil is. They have perhaps twenty
 * seconds, and every other screen drops them straight into data — a timeline of
 * events for a person they have never heard of, a registry of agents whose names
 * mean nothing yet. Reverse-engineering a system's purpose from its contents is
 * work, and a reader who has to do it usually leaves instead.
 *
 * So this page does three things in order: the problem in the words of the
 * person who has it, proof the system is doing something right now, and a way
 * into each screen that says what is there and what to look for.
 */

interface RunRow {
  run_id: string;
  status?: string;
  kind?: string;
  created_at?: string;
}

const SCREENS = [
  {
    href: "/timeline/",
    title: "Timeline",
    who: "for the caregiver",
    what: "Everything the fleet did, week by week, in plain language.",
    look: "The amber rows are the only ones that need you.",
  },
  {
    href: "/intake/",
    title: "Intake",
    who: "for the caregiver",
    what: "Drop in a photo, a recording or a scan and watch three agents read it.",
    look: "The pairing — what arrived on the left, what was understood on the right.",
  },
  {
    href: "/approvals/",
    title: "Approvals",
    who: "for the caregiver",
    what: "The things the fleet refused to do without a person.",
    look: "Why you are being asked. An agent that stops is only trustworthy if it can say what stopped it.",
  },
  {
    href: "/fleet/",
    title: "Fleet",
    who: "for whoever is accountable",
    what: "The five agents, the four data boundaries, and every version decision.",
    look: "The dashed red line crossing a boundary — and the version that scored higher and was rejected anyway.",
  },
  {
    href: "/trace/",
    title: "Trace",
    who: "for whoever is accountable",
    what: "Every decision one run made, in the order it made them.",
    look: "The red rows. That is where something was refused, and why.",
  },
];

interface Step {
  step_id: string;
  status?: string;
  payload?: { agent?: string } | null;
  result?: { elapsed_s?: number; tokens?: number; tools?: number } | null;
}

/**
 * The newest run, shown as the chain of agents that handled it.
 *
 * A separate component rather than another hook in the page, because the fetch
 * has no meaningful path until a run id exists — mounting it only when there is
 * one is simpler than teaching the loader to skip.
 *
 * This is the landing page's strongest evidence. The paragraph above claims five
 * agents; a reader has no reason to believe it, and every other screen shows
 * output that one capable assistant could equally have produced. Naming the
 * agents that touched the most recent real run, with the seconds each spent, is
 * the difference between an assertion and a demonstration.
 */
function LatestRun({ runId }: { runId: string }) {
  const trace = useLive<{ steps: Step[]; kind?: string; status?: string }>(
    `/runs/${runId}/trace`,
    20_000,
  );
  const hops = useHops(trace.data?.steps ?? []);
  if (hops.length === 0) return null;

  return (
    <div className="px-4 pb-4 border-t border-[var(--line-soft)] pt-3.5">
      <div className="flex items-baseline gap-2 flex-wrap mb-2">
        <span className="eyebrow">The most recent run</span>
        <span className="text-[0.84rem] text-[var(--text-2)]">
          {agentCount(hops)} agents, one after another — each with its own tools and its own
          department&rsquo;s data
        </span>
      </div>
      <Handoff hops={hops} />
    </div>
  );
}

export default function OverviewPage() {
  const runs = useLive<{ runs: RunRow[] }>("/runs?limit=50", 20_000);

  if (runs.status === "loading") return <LoadingScreen what="the fleet" />;
  if (runs.status === "error" || !runs.data) {
    return <ErrorScreen what="what the fleet has run" error={runs.error} onRetry={runs.retry} />;
  }

  const rows = runs.data.runs;
  const held = rows.filter((r) => r.status === "awaiting_human").length;
  const done = rows.filter((r) => r.status === "done").length;

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-4 py-10">
        <p className="eyebrow mb-3">An agent fleet that keeps watch</p>
        <h1 className="text-[1.9rem] font-medium tracking-tight leading-tight">
          Looking after someone at home is an operations job
          <br />
          nobody trained you for.
        </h1>

        <p className="mt-4 text-[1.02rem] leading-relaxed text-[var(--text-1)] max-w-[42rem]">
          Appointments at three different providers. Eight medications with overlapping
          schedules. Insurance paperwork with the deadline buried in paragraph three. Lab
          results that arrive as a crooked photo of a printed page, and notes recorded as a
          voice memo in a hospital corridor.
        </p>
        <p className="mt-3 text-[1.02rem] leading-relaxed text-[var(--text-1)] max-w-[42rem]">
          <em className="not-italic text-[var(--text-0)] font-medium">
            Vigil is five agents that read all of it and act on it
          </em>{" "}
          — running for weeks in the background, deciding what to do next, and stopping to
          ask you before anything that cannot be undone.
        </p>

        {/* Proof, not a claim. These numbers come from the deployed audit trail. */}
        <div className="panel mt-8 overflow-hidden">
          <div className="panel-head">
            <span className="eyebrow">Right now</span>
            {runs.error && (
              <span className="chip chip-wait" title={runs.error}>
                reconnecting
              </span>
            )}
          </div>
          <div className="p-4 grid grid-cols-3 gap-4">
            <div>
              <p className="mono text-[1.6rem] leading-none">{rows.length}</p>
              <p className="eyebrow mt-1.5">runs handled</p>
            </div>
            <div>
              <p
                className="mono text-[1.6rem] leading-none"
                style={held > 0 ? { color: "var(--amber)" } : undefined}
              >
                {held}
              </p>
              <p className="eyebrow mt-1.5">waiting on a human</p>
            </div>
            <div>
              <p className="mono text-[1.6rem] leading-none">{done}</p>
              <p className="eyebrow mt-1.5">finished on their own</p>
            </div>
          </div>
          {rows.length > 0 && <LatestRun runId={rows[0].run_id} />}
        </div>

        {/* Where to go, and what to look at when you get there. */}
        <div className="flex items-center gap-3 mt-9 mb-3">
          <span className="eyebrow">Five screens</span>
          <span className="h-px flex-1 bg-[var(--line-soft)]" />
        </div>

        <div className="space-y-2.5">
          {SCREENS.map((screen) => (
            <Link
              key={screen.href}
              href={screen.href}
              className="panel block p-4 transition-colors hover:bg-[var(--bg-2)]"
            >
              <div className="flex items-baseline gap-2.5 flex-wrap">
                <h2 className="text-[1rem] font-medium">{screen.title}</h2>
                <span className="eyebrow">{screen.who}</span>
              </div>
              <p className="mt-1 text-[0.95rem] text-[var(--text-1)]">{screen.what}</p>
              <p className="mt-1.5 text-[0.88rem]" style={{ color: "var(--amber)" }}>
                Look for: {screen.look}
              </p>
            </Link>
          ))}
        </div>

        <p className="mt-8 text-[0.86rem] text-[var(--text-2)] leading-relaxed">
          Every document, photograph and recording here is synthetic. Vigil coordinates
          admin; it does not give medical advice, and every clinical change waits for a
          person.
        </p>
      </div>
    </div>
  );
}
