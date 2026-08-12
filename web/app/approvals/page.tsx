"use client";

import { useCallback, useState } from "react";
import { ScreenIntro } from "@/components/ScreenIntro";
import { ErrorScreen, LoadingScreen } from "@/components/Screen";
import { decideApproval } from "@/lib/api";
import { useLive } from "@/lib/live";
import { DEPARTMENT_LABEL, type Department } from "@/lib/types";

/**
 * Approvals — medium density.
 *
 * Enough context to decide and not one field more. The card answers four
 * questions in the order a person actually asks them: what is about to happen,
 * why, why am I being asked at all, and what is it standing on.
 *
 * The third matters most and is the one usually missing. An agent that stops is
 * only trustworthy if it can say what made it stop — "policy gates every
 * irreversible external action" is a reason; a spinner is not.
 *
 * Deciding here records the decision and returns. It does not execute anything:
 * the run picks the settled approval up on its next tick, so an approval granted
 * while the worker is down is not lost, and a worker that comes back up twice
 * does not act twice.
 */

interface LiveApproval {
  id: string;
  requested_by: string;
  action: string;
  scope?: string;
  gate_reason?: string;
  rule_id?: string;
  confidence?: number;
  risk?: string;
  run_id?: string;
  payload?: Record<string, unknown>;
}

const RISK_CHIP: Record<string, string> = {
  low: "chip chip-ok",
  medium: "chip chip-wait",
  high: "chip chip-deny",
};

const DEPARTMENT_OF: Record<string, Department> = {
  "intake-agent": "family",
  "meds-agent": "clinical",
  "benefits-agent": "benefits",
  watchdog: "audit",
  orchestrator: "family",
};

type Decided = "approved" | "denied";

function Card({
  id,
  requestedBy,
  department,
  action,
  rationale,
  gateReason,
  ruleId,
  risk,
  confidence,
  evidence,
  runId,
  decided,
  busy,
  onDecide,
}: {
  id: string;
  requestedBy: string;
  department: Department;
  action: string;
  rationale?: string;
  gateReason?: string;
  ruleId?: string;
  risk?: string;
  confidence?: number;
  evidence?: { label: string; source_uri: string }[];
  runId?: string;
  decided?: Decided;
  busy?: boolean;
  onDecide?: (approved: boolean) => void;
}) {
  const lowConfidence = typeof confidence === "number" && confidence < 0.6;

  return (
    <article
      className={`panel dept-${department} overflow-hidden`}
      style={decided ? { opacity: 0.6 } : undefined}
    >
      <div className="panel-head">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="dept-bar h-4" aria-hidden />
          <span className="mono text-[0.8rem] text-[var(--text-1)]">{requestedBy}</span>
          <span className="eyebrow">{DEPARTMENT_LABEL[department]}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {risk && <span className={RISK_CHIP[risk] ?? "chip chip-muted"}>{risk} risk</span>}
          {typeof confidence === "number" && (
            <span className={lowConfidence ? "chip chip-deny" : "chip chip-muted"}>
              conf {confidence.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      <div className="p-4">
        <h2 className="text-[1.02rem] font-medium">{action}</h2>
        {rationale && (
          <p className="mt-2 text-[0.9rem] leading-relaxed text-[var(--text-1)]">{rationale}</p>
        )}

        {gateReason && (
          <div
            className="mt-3 rounded-md border px-3 py-2.5"
            style={{
              borderColor: "color-mix(in oklab, var(--amber) 30%, transparent)",
              background: "color-mix(in oklab, var(--amber) 6%, transparent)",
            }}
          >
            <div className="flex items-baseline justify-between gap-2">
              <p className="eyebrow mb-1">Why you are being asked</p>
              {ruleId && <span className="mono text-[0.7rem] text-[var(--text-2)]">{ruleId}</span>}
            </div>
            <p className="text-[0.88rem] leading-relaxed text-[var(--text-1)]">{gateReason}</p>
          </div>
        )}

        {evidence && evidence.length > 0 && (
          <div className="mt-3">
            <p className="eyebrow mb-1.5">Standing on</p>
            <ul className="space-y-1">
              {evidence.map((e) => (
                <li key={e.source_uri} className="flex items-baseline gap-2 text-[0.86rem]">
                  <span className="text-[var(--text-2)]" aria-hidden>
                    ↳
                  </span>
                  <span className="text-[var(--text-1)]">{e.label}</span>
                  <span className="mono text-[0.72rem] text-[var(--text-2)] truncate">
                    {e.source_uri}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 flex items-center gap-2 flex-wrap">
          {decided ? (
            <span className={decided === "approved" ? "chip chip-ok" : "chip chip-deny"}>
              {decided} — the run picks this up on its next tick
            </span>
          ) : (
            <>
              <button
                type="button"
                className="btn btn-approve"
                disabled={busy || !onDecide}
                onClick={() => onDecide?.(true)}
              >
                {busy ? "…" : "✓ Approve"}
              </button>
              <button
                type="button"
                className="btn btn-deny"
                disabled={busy || !onDecide}
                onClick={() => onDecide?.(false)}
              >
                ⊘ Deny
              </button>
            </>
          )}
          {runId && (
            <span className="mono text-[0.72rem] text-[var(--text-2)] ml-auto">{runId}</span>
          )}
          <span className="sr-only">{id}</span>
        </div>
      </div>
    </article>
  );
}

export default function ApprovalsPage() {
  const [decided, setDecided] = useState<Record<string, Decided>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loaded = useLive<{ approvals: LiveApproval[] }>("/approvals?status=pending", 15_000);

  const decide = useCallback(async (id: string, approved: boolean) => {
    setBusy(id);
    setError(null);
    try {
      await decideApproval(id, approved);
      setDecided((current) => ({ ...current, [id]: approved ? "approved" : "denied" }));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(null);
    }
  }, []);

  if (loaded.status === "loading") return <LoadingScreen what="the approvals queue" />;
  if (loaded.status === "error" || !loaded.data) {
    return (
      <ErrorScreen what="the approvals queue" error={loaded.error} onRetry={loaded.retry} />
    );
  }

  const pending = loaded.data.approvals;
  const count = pending.length;

  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-6">
        <ScreenIntro
          title="Waiting on you"
          aside={
            <>
              {loaded.error && (
                <span className="chip chip-wait" title={loaded.error}>
                  reconnecting
                </span>
              )}
              <span className="eyebrow">{count} pending</span>
            </>
          }
        >
          {count === 0 ? (
            <>
              Nothing is waiting. Everything the fleet did, it did on its own — and every one
              of those decisions is on the Trace screen if you want to check it.
            </>
          ) : (
            <>
              The things the fleet refused to do without a person. Each card says what would
              happen, what it is based on, and — the part usually missing —{" "}
              <em>why you are being asked at all</em>.
            </>
          )}
        </ScreenIntro>

        {error && (
          <p className="mb-4 text-[0.86rem]" style={{ color: "var(--rose)" }}>
            {error}
          </p>
        )}

        <div className="space-y-4">
          {pending.map((a) => (
            <Card
              key={a.id}
              id={a.id}
              requestedBy={a.requested_by}
              department={DEPARTMENT_OF[a.requested_by] ?? "family"}
              action={a.action}
              gateReason={a.gate_reason}
              ruleId={a.rule_id}
              risk={a.risk}
              confidence={a.confidence}
              runId={a.run_id}
              decided={decided[a.id]}
              busy={busy === a.id}
              onDecide={(approved) => decide(a.id, approved)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
