"use client";

import { useCallback, useEffect, useState } from "react";
import { read } from "./api";
import type { Department, Decision, TimelineEvent } from "./types";

/**
 * One reader for every screen: loading, then either data or an error.
 *
 * There is no third outcome any more. When this returned a fixture on failure,
 * a screen could look complete while the backend was unreachable, and for the
 * whole life of the deployment that is exactly what happened — the browser could
 * not authenticate, every request failed, and every page quietly rendered
 * committed sample data instead. The failure had nowhere to surface.
 *
 * Client-side rather than at build time, because the UI is a static export:
 * anything fetched during the build would be frozen at the moment the image was
 * made, and a judge opening the page after a demo run should see that run.
 */

export interface Live<T> {
  status: "loading" | "ready" | "error";
  data: T | null;
  error?: string;
  /** Re-run the request now, without waiting for the next poll. */
  retry: () => void;
}

export function useLive<T>(path: string | null, pollMs = 0): Live<T> {
  const [state, setState] = useState<{ status: Live<T>["status"]; data: T | null; error?: string }>({
    status: "loading",
    data: null,
  });
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  useEffect(() => {
    if (!path) return;
    let cancelled = false;

    const load = async () => {
      try {
        const data = await read<T>(path);
        if (!cancelled) setState({ status: "ready", data });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        if (cancelled) return;
        // A poll that fails after a good read keeps the data on screen and says
        // so, rather than throwing away a working view over one bad request.
        setState((prev) =>
          prev.status === "ready"
            ? { status: "ready", data: prev.data, error: message }
            : { status: "error", data: null, error: message },
        );
      }
    };

    load();
    if (!pollMs) {
      return () => {
        cancelled = true;
      };
    }

    // Polling exists for one reason: a fleet run takes about a minute, and a
    // screen frozen for a minute reads as broken. Cheap reads, generous
    // interval — this is a demo surface, not a dashboard for a thousand users.
    const timer = setInterval(load, pollMs);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [path, pollMs, attempt]);

  return { ...state, retry };
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
