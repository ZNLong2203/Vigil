"use client";

import { useEffect, useState } from "react";
import { type Loaded, isConfigured, withFallback } from "./api";
import type { Department, Decision, TimelineEvent } from "./types";

/**
 * Read live data if there is any, otherwise the committed fixtures.
 *
 * Client-side rather than at build time on purpose: the UI is a static export,
 * so anything fetched during the build would be frozen at the moment the image
 * was made. A judge opening the page an hour after a demo run should see that
 * run, not a snapshot of an empty database.
 */
export function useLoaded<T>(path: string, fixture: T, pollMs = 0): Loaded<T> & { loading: boolean } {
  const [state, setState] = useState<Loaded<T>>({ data: fixture, source: "fixture" });
  const [loading, setLoading] = useState(isConfigured());

  useEffect(() => {
    let cancelled = false;

    const read = async () => {
      const result = await withFallback(path, fixture);
      if (!cancelled) {
        setState(result);
        setLoading(false);
      }
    };

    read();
    if (!pollMs) return () => {
      cancelled = true;
    };

    // Polling exists for one reason: a fleet run takes about a minute, and a
    // screen frozen for a minute reads as broken. Cheap reads, generous
    // interval — this is a demo surface, not a dashboard for a thousand users.
    const timer = setInterval(read, pollMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, pollMs]);

  return { ...state, loading };
}

// ── Mapping the audit trail onto the timeline ────────────────────────────────
//
// The audit log is already a chronological record of decisions, which is what
// the timeline shows — so the timeline is a rendering of the audit trail rather
// than a second source of truth kept in step with it. The alternative, a
// purpose-built timeline collection, would eventually disagree with the audit
// log, and the audit log is the one that has to be right.

interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  decision: string;
  details?: Record<string, unknown>;
  at?: string;
  trace_id?: string;
}

const ACTOR_DEPARTMENT: Record<string, Department> = {
  api: "family",
  worker: "family",
  "intake-agent": "family",
  orchestrator: "family",
  "meds-agent": "clinical",
  "benefits-agent": "benefits",
  watchdog: "audit",
  "trust-boundary": "audit",
  "action-gate": "audit",
};

/** Plain-language titles. An audit action is a machine key; a caregiver reading
 *  the timeline should not have to decode `guardrail.blocked`. */
const TITLES: Record<string, string> = {
  "event.ingested": "Document received",
  "guardrail.blocked": "Injected instructions blocked in a document",
  "tool.denied": "Cross-department read denied",
  "tool.loop_broken": "Agent loop broken",
  "escalation.raised": "Escalated for a human decision",
  "watchdog.escalated": "Verification escalated",
  "proposal.created": "Schedule change proposed",
  "draft.created": "Document drafted, awaiting approval",
  "action.awaiting_approval": "Waiting on your approval",
  "action.denied": "Action denied by policy",
  "action.duplicate_suppressed": "Duplicate suppressed",
  "step.completed": "Step completed",
  "run.finished": "Run finished",
  "budget.exceeded": "Stopped: run budget exhausted",
  "delegation.unknown_agent": "Plan named an agent that does not exist",
};

const DECISIONS = new Set([
  "accepted",
  "done",
  "skipped",
  "failed",
  "blocked",
  "denied",
  "escalated",
  "awaiting_approval",
]);

export function auditToTimeline(entries: AuditEntry[]): TimelineEvent[] {
  return entries
    .filter((e) => e.at)
    .map((entry) => {
      const details = entry.details ?? {};
      const decision = (DECISIONS.has(entry.decision) ? entry.decision : "done") as Decision;

      return {
        id: entry.id,
        at: entry.at as string,
        department: ACTOR_DEPARTMENT[entry.actor] ?? "audit",
        actor: entry.actor as TimelineEvent["actor"],
        title: TITLES[entry.action] ?? entry.action.replace(/[._]/g, " "),
        detail: describe(details),
        decision,
        source_uri: typeof details.source_uri === "string" ? details.source_uri : undefined,
        run_id: typeof details.run_id === "string" ? details.run_id : undefined,
      };
    })
    .sort((a, b) => a.at.localeCompare(b.at));
}

function describe(details: Record<string, unknown>): string | undefined {
  const interesting = ["summary", "reason", "error", "kinds", "tool", "excerpt", "requested"];
  const parts = interesting
    .filter((key) => details[key] != null)
    .map((key) => String(details[key]))
    .filter((value) => value.length > 0);
  return parts.length ? parts.join(" · ").slice(0, 400) : undefined;
}
