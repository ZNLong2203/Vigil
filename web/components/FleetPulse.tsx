"use client";

import { useLive } from "@/lib/live";

/**
 * The dot beside the wordmark. It means something or it does not move.
 *
 * The first version pulsed permanently. That broke the rule this design system
 * opens with — motion carries information or it does not happen — and it broke
 * it in the most misleading way available: a signal that is always on is
 * indistinguishable from decoration, except that a viewer spends a moment
 * wondering what it is telling them before concluding it is telling them
 * nothing.
 *
 * Now it reflects the fleet. Something running, it pulses. Something waiting on
 * a person, it holds amber and still. Nothing happening, it is a quiet dot. A
 * glance at the corner answers "is anything going on" without opening a screen,
 * which is the only reason to put a live indicator in a header at all.
 */

interface RunRow {
  status?: string;
}

export function FleetPulse() {
  const runs = useLive<{ runs: RunRow[] }>("/runs?limit=20", 20_000);

  const rows = runs.data?.runs ?? [];
  const unreachable = runs.status === "error";
  const working = rows.some((r) => r.status === "running");
  const waiting = rows.some((r) => r.status === "awaiting_human");

  const [colour, label] = unreachable
    ? ["var(--rose)", "the service is not answering"]
    : working
      ? ["var(--phosphor)", "an agent is working"]
      : waiting
        ? ["var(--amber)", "waiting on a human"]
        : ["var(--text-2)", "idle"];

  return (
    <span
      className={working ? "live-dot" : ""}
      title={label}
      aria-label={`Fleet: ${label}`}
      style={{
        width: "0.5rem",
        height: "0.5rem",
        borderRadius: "999px",
        background: colour,
        display: "inline-block",
        flexShrink: 0,
      }}
    />
  );
}
