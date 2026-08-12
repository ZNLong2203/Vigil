import { APPROVALS } from "@/lib/mock";
import { DEPARTMENT_LABEL, type Approval } from "@/lib/types";

/**
 * Approvals — medium density.
 *
 * Enough context to decide, and not one field more. The card has to answer four
 * questions in the order a person actually asks them: what is about to happen,
 * why, why am I being asked at all, and what is it standing on.
 *
 * The gate reason matters more than it looks. An agent that stops is only
 * trustworthy if it can say what made it stop.
 */

const RISK_CHIP: Record<Approval["risk"], string> = {
  low: "chip chip-ok",
  medium: "chip chip-wait",
  high: "chip chip-deny",
};

function ApprovalCard({ item }: { item: Approval }) {
  const lowConfidence = item.confidence < 0.6;

  return (
    <article className={`panel dept-${item.department} overflow-hidden`}>
      <div className="panel-head">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="dept-bar h-4" aria-hidden />
          <span className="mono text-[0.8rem] text-[var(--text-1)]">{item.requested_by}</span>
          <span className="eyebrow">{DEPARTMENT_LABEL[item.department]}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={RISK_CHIP[item.risk]}>{item.risk} risk</span>
          <span className={lowConfidence ? "chip chip-deny" : "chip chip-muted"}>
            conf {item.confidence.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="p-4">
        <h2 className="text-[1.02rem] font-medium">{item.action}</h2>
        <p className="mt-2 text-[0.9rem] leading-relaxed text-[var(--text-1)]">{item.rationale}</p>

        <div
          className="mt-3 rounded-md border px-3 py-2.5"
          style={{
            borderColor: "color-mix(in oklab, var(--amber) 30%, transparent)",
            background: "color-mix(in oklab, var(--amber) 6%, transparent)",
          }}
        >
          <p className="eyebrow mb-1">Why you are being asked</p>
          <p className="text-[0.88rem] leading-relaxed text-[var(--text-1)]">{item.gate_reason}</p>
        </div>

        <div className="mt-3">
          <p className="eyebrow mb-1.5">Standing on</p>
          <ul className="space-y-1">
            {item.evidence.map((e) => (
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

        <div className="mt-4 flex items-center gap-2 flex-wrap">
          <button type="button" className="btn btn-approve">
            ✓ Approve
          </button>
          <button type="button" className="btn btn-deny">
            ⊘ Deny
          </button>
          <button type="button" className="btn">
            Ask for more
          </button>
          <span className="mono text-[0.72rem] text-[var(--text-2)] ml-auto">{item.run_id}</span>
        </div>
      </div>
    </article>
  );
}

export default function ApprovalsPage() {
  return (
    <div data-density="calm" className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-6">
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="text-lg font-medium">Waiting on you</h1>
          <span className="eyebrow">{APPROVALS.length} pending</span>
        </div>
        <p className="text-[var(--text-1)] text-[0.9rem] mt-1 mb-5">
          Everything else the fleet handled on its own. These stopped because policy said a person
          decides.
        </p>

        <div className="space-y-4">
          {APPROVALS.map((item) => (
            <ApprovalCard key={item.id} item={item} />
          ))}
        </div>
      </div>
    </div>
  );
}
