"""The action gate: the single door between an agent's intent and the world.

Nothing an agent decides reaches a calendar, a document or a person except
through `submit`. One door, so there is one place that claims idempotency, asks
the policy engine, records the intent, and knows how to undo what it started.

Ordering inside `submit` is the whole design:

    policy → claim → execute → complete
                 ↘ on failure: compensate in reverse, then release the claim

Policy runs *before* the claim so a denied action never consumes a key. Claiming
runs *before* execution so a crash between them leaves the key held and the
resumed run skips the step instead of repeating it (see ADR 002). Compensation
runs in reverse order because undoing step 3 before step 2 is how you end up in a
state neither step ever produced.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from vigil.policy import ActionRequest, PolicyDecision, evaluate
from vigil.state import StepAlreadyDone, audit, claim_step, complete_step, db, fail_step, now
from vigil.telemetry import log, span

_log = log("vigil.actions")


@dataclass(slots=True)
class ActionOutcome:
    status: str  # done | awaiting_approval | denied | duplicate | failed
    decision: PolicyDecision | None = None
    result: dict[str, Any] | None = None
    approval_id: str | None = None
    error: str | None = None

    @property
    def happened(self) -> bool:
        """True when the world changed — or already had."""
        return self.status in {"done", "duplicate"}


@dataclass(slots=True)
class Saga:
    """Compensations for the steps taken so far, newest first.

    Registered *after* a step succeeds, not before: there is nothing to undo
    until something has been done, and a compensation for a step that never ran
    is its own kind of bug.
    """

    run_id: str
    _steps: list[tuple[str, Callable[[], None]]] = field(default_factory=list)

    def record(self, label: str, undo: Callable[[], None]) -> None:
        self._steps.append((label, undo))

    def compensate(self, reason: str) -> list[str]:
        """Unwind in reverse. Returns the labels that were undone.

        A compensation that itself fails is logged and the unwind continues —
        stopping halfway would leave the system in a state that is worse than
        either end of the operation.
        """
        undone: list[str] = []
        for label, undo in reversed(self._steps):
            try:
                undo()
                undone.append(label)
                audit(
                    "saga.compensated",
                    actor="action-gate",
                    decision="done",
                    run_id=self.run_id,
                    step=label,
                    reason=reason,
                )
            except Exception as exc:
                _log.error(
                    "saga.compensation_failed", run_id=self.run_id, step=label, error=str(exc)
                )
                audit(
                    "saga.compensation_failed",
                    actor="action-gate",
                    decision="failed",
                    run_id=self.run_id,
                    step=label,
                    error=str(exc),
                )
        self._steps.clear()
        return undone


def submit(
    request: ActionRequest,
    execute: Callable[[], dict[str, Any]],
    *,
    step_id: str | None = None,
    saga: Saga | None = None,
    compensate: Callable[[], None] | None = None,
) -> ActionOutcome:
    """Put one intended action through the gate.

    Args:
        request: What the agent wants to do, and how sure it is.
        execute: Performs the side effect. Called only on auto_allow.
        step_id: Idempotency step id. Defaults to the action name.
        saga: Optional saga to register this step's compensation with.
        compensate: How to undo this step, if it can be undone.
    """
    step = step_id or request.action
    payload = request.payload or {}

    with span(
        "action.gate",
        run_id=request.run_id,
        actor=request.actor,
        intent=request.action,
        scope=str(request.scope),
    ):
        decision = evaluate(request)

        if decision.blocked:
            audit(
                "action.denied",
                actor=request.actor,
                decision="denied",
                run_id=request.run_id,
                intent=request.action,
                rule_id=decision.rule_id,
            )
            return ActionOutcome(status="denied", decision=decision, error=decision.reason)

        if decision.needs_human:
            approval_id = _request_approval(request, decision)
            audit(
                "action.awaiting_approval",
                actor=request.actor,
                decision="awaiting_approval",
                run_id=request.run_id,
                intent=request.action,
                rule_id=decision.rule_id,
            )
            return ActionOutcome(
                status="awaiting_approval", decision=decision, approval_id=approval_id
            )

        try:
            key = claim_step(request.run_id, step, payload)
        except StepAlreadyDone:
            # The work is done; this attempt is a replay. Reporting success is
            # correct — the caller asked for a state, not for an execution.
            audit(
                "action.duplicate_suppressed",
                actor=request.actor,
                decision="skipped",
                run_id=request.run_id,
                intent=request.action,
            )
            return ActionOutcome(status="duplicate", decision=decision)

        try:
            result = execute()
        except Exception as exc:
            fail_step(request.run_id, step, key, str(exc))
            if saga:
                saga.compensate(reason=f"{request.action} failed: {exc}")
            audit(
                "action.failed",
                actor=request.actor,
                decision="failed",
                run_id=request.run_id,
                intent=request.action,
                error=str(exc),
            )
            return ActionOutcome(status="failed", decision=decision, error=str(exc))

        complete_step(request.run_id, step, key, result)
        if saga and compensate:
            saga.record(request.action, compensate)

        audit(
            "action.completed",
            actor=request.actor,
            decision="done",
            run_id=request.run_id,
            intent=request.action,
            rule_id=decision.rule_id,
        )
        return ActionOutcome(status="done", decision=decision, result=result)


def _request_approval(request: ActionRequest, decision: PolicyDecision) -> str:
    """Record what the agent wanted, why, and what made us ask.

    `gate_reason` is stored separately from the agent's own rationale because
    they answer different questions. The rationale is why the action is a good
    idea; the gate reason is why a person is being interrupted about it. A person
    deciding at 11pm needs the second one first.
    """
    approval_id = uuid.uuid4().hex
    db().collection("approvals").document(approval_id).set(
        {
            "run_id": request.run_id,
            "requested_by": request.actor,
            "action": request.action,
            "scope": str(request.scope),
            "payload": request.payload or {},
            "confidence": request.confidence,
            "risk": str(request.risk),
            "gate_reason": decision.reason,
            "rule_id": decision.rule_id,
            "status": "pending",
            "requested_at": now(),
        }
    )
    return approval_id


def resolve_approval(approval_id: str, approved: bool, decided_by: str) -> dict[str, Any]:
    """Record a human's decision.

    This does not execute anything. The run resumes on its own next tick and
    finds the approval settled — which means an approval granted while the worker
    is down is not lost, and a worker that comes back up twice does not act twice.
    """
    ref = db().collection("approvals").document(approval_id)
    snapshot = ref.get()
    if not snapshot.exists:
        return {"ok": False, "error": f"no approval {approval_id}"}

    record = snapshot.to_dict() or {}
    if record.get("status") != "pending":
        return {
            "ok": False,
            "error": f"already {record.get('status')}",
            "status": record.get("status"),
        }

    status = "approved" if approved else "denied"
    ref.update({"status": status, "decided_by": decided_by, "decided_at": now()})
    audit(
        "approval.resolved",
        actor=decided_by,
        decision=status,
        run_id=record.get("run_id"),
        approval_id=approval_id,
        intent=record.get("action"),
    )
    return {"ok": True, "status": status}
