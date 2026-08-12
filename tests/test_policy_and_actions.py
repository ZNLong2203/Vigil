"""Policy ordering, the action gate, and the saga.

All offline. The gate's Firestore calls are stubbed, because what is being
asserted here is decision logic and ordering, not persistence.

The test that matters most is `test_confidence_cannot_buy_past_a_clinical_gate`.
Every other rule in this engine could be renegotiated; that one is the reason a
caregiver could trust the system at all.
"""

from __future__ import annotations

from typing import Any

import pytest

from vigil import actions as act
from vigil.actions import ActionOutcome, Saga, submit
from vigil.fleet.scopes import Scope
from vigil.policy import (
    CONFIDENCE_FLOOR,
    ActionRequest,
    Risk,
    Verdict,
    evaluate,
)


@pytest.fixture(autouse=True)
def _stub_persistence(monkeypatch):
    """Replace everything that touches Firestore. Returns the audit trail."""
    trail: list[dict[str, Any]] = []
    claimed: set[tuple[str, str]] = set()

    def fake_audit(action: str, actor: str, decision: str, **details: Any) -> str:
        trail.append({"action": action, "actor": actor, "decision": decision, **details})
        return "entry"

    def fake_claim(run_id: str, step_id: str, payload: dict) -> str:
        if (run_id, step_id) in claimed:
            raise act.StepAlreadyDone("already")
        claimed.add((run_id, step_id))
        return f"key-{step_id}"

    monkeypatch.setattr(act, "audit", fake_audit)
    monkeypatch.setattr(act, "claim_step", fake_claim)
    monkeypatch.setattr(act, "complete_step", lambda *a, **k: None)
    monkeypatch.setattr(act, "fail_step", lambda *a, **k: None)
    monkeypatch.setattr(act, "_request_approval", lambda *a, **k: "approval-1")
    return trail


def request(**kw) -> ActionRequest:
    base = {
        "run_id": "r-1",
        "actor": "benefits-agent",
        "action": "draft_document",
        "scope": Scope.DOC_GENERATE,
        "confidence": 0.95,
        "risk": Risk.LOW,
    }
    return ActionRequest(**{**base, **kw})


# ── Policy ordering ──────────────────────────────────────────────────────────


def test_confidence_cannot_buy_past_a_clinical_gate():
    """The rule the whole safety story rests on. A perfectly confident agent is
    still not allowed to change a medication on its own — certainty is what a
    confident hallucination feels like from the inside."""
    decision = evaluate(
        request(
            actor="meds-agent",
            action="propose_schedule_change",
            scope=Scope.SCHEDULE_WRITE,
            confidence=1.0,
            risk=Risk.LOW,
        )
    )
    assert decision.verdict is Verdict.REQUIRE_APPROVAL
    assert decision.rule_id == "approve.clinical"


def test_unscoped_action_is_denied_not_merely_gated():
    """Defence in depth behind the toolbelt: if a request for a capability the
    agent does not hold reaches here, something upstream is broken and the safe
    reading is that the request cannot be trusted."""
    decision = evaluate(request(actor="benefits-agent", scope=Scope.MEDGRAPH_READ, confidence=1.0))
    assert decision.verdict is Verdict.DENY
    assert decision.rule_id == "deny.unscoped"


def test_irreversible_effects_always_ask():
    decision = evaluate(request(confidence=0.99))
    assert decision.verdict is Verdict.REQUIRE_APPROVAL
    assert decision.rule_id == "approve.external"


def test_low_confidence_asks_even_when_reversible():
    decision = evaluate(
        request(
            actor="intake-agent",
            action="write_staging",
            scope=Scope.STAGING_WRITE,
            confidence=CONFIDENCE_FLOOR - 0.01,
        )
    )
    assert decision.rule_id == "approve.low_confidence"


def test_reversible_and_confident_proceeds():
    decision = evaluate(
        request(
            actor="intake-agent", action="write_staging", scope=Scope.STAGING_WRITE, confidence=0.9
        )
    )
    assert decision.verdict is Verdict.AUTO_ALLOW


def test_every_decision_names_the_rule_that_made_it():
    """ "Denied" is not an auditable statement. "Denied by deny.unscoped" is."""
    for req in (
        request(),
        request(actor="meds-agent", scope=Scope.SCHEDULE_WRITE),
        request(actor="benefits-agent", scope=Scope.MEDGRAPH_READ),
        request(actor="intake-agent", scope=Scope.STAGING_WRITE, confidence=0.2),
    ):
        assert evaluate(req).rule_id


# ── The gate ─────────────────────────────────────────────────────────────────


def test_denied_action_never_runs(_stub_persistence):
    ran = False

    def execute() -> dict:
        nonlocal ran
        ran = True
        return {}

    outcome = submit(request(actor="benefits-agent", scope=Scope.MEDGRAPH_READ), execute)
    assert outcome.status == "denied"
    assert ran is False


def test_a_denied_action_does_not_consume_an_idempotency_key(_stub_persistence):
    """Policy runs before the claim. If a denial burned a key, a later legitimate
    attempt at the same step would be mistaken for a replay and skipped."""
    req = request(actor="benefits-agent", scope=Scope.MEDGRAPH_READ)
    assert submit(req, lambda: {}).status == "denied"

    # Same run and step, now legitimately scoped: must still be claimable.
    ok = submit(
        request(action="draft_document", scope=Scope.BENEFITS_READ, confidence=0.9),
        lambda: {"drafted": True},
        step_id="draft_document",
    )
    assert ok.status == "done"


def test_gated_action_waits_for_a_human_without_running(_stub_persistence):
    ran = False

    def execute() -> dict:
        nonlocal ran
        ran = True
        return {}

    outcome = submit(
        request(
            actor="meds-agent",
            action="propose_schedule_change",
            scope=Scope.SCHEDULE_WRITE,
            confidence=1.0,
        ),
        execute,
    )
    assert outcome.status == "awaiting_approval"
    assert outcome.approval_id == "approval-1"
    assert ran is False


def test_replay_reports_success_without_running_again(_stub_persistence):
    calls = 0

    def execute() -> dict:
        nonlocal calls
        calls += 1
        return {"n": calls}

    allow = request(
        actor="intake-agent", action="write_staging", scope=Scope.STAGING_WRITE, confidence=0.9
    )
    first = submit(allow, execute)
    second = submit(allow, execute)

    assert first.status == "done"
    assert second.status == "duplicate"
    assert second.happened, "a replay must read as success — the state is what was asked for"
    assert calls == 1


# ── Saga ─────────────────────────────────────────────────────────────────────


def test_compensations_unwind_in_reverse(_stub_persistence):
    order: list[str] = []
    saga = Saga(run_id="r-1")

    for n in (1, 2, 3):
        submit(
            request(
                actor="intake-agent", action=f"step{n}", scope=Scope.STAGING_WRITE, confidence=0.9
            ),
            lambda: {"ok": True},
            step_id=f"step{n}",
            saga=saga,
            compensate=lambda n=n: order.append(f"undo{n}"),
        )

    saga.compensate(reason="downstream failure")
    assert order == ["undo3", "undo2", "undo1"]


def test_a_failing_compensation_does_not_stop_the_unwind(_stub_persistence):
    """Stopping halfway leaves the system in a state neither end of the operation
    ever produced."""
    order: list[str] = []
    saga = Saga(run_id="r-1")
    saga.record("first", lambda: order.append("undo1"))
    saga.record("second", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    saga.record("third", lambda: order.append("undo3"))

    undone = saga.compensate(reason="test")
    assert order == ["undo3", "undo1"]
    assert undone == ["third", "first"]


def test_failure_triggers_compensation_and_reports_it(_stub_persistence):
    order: list[str] = []
    saga = Saga(run_id="r-1")
    saga.record("earlier", lambda: order.append("undone"))

    outcome: ActionOutcome = submit(
        request(
            actor="intake-agent", action="write_staging", scope=Scope.STAGING_WRITE, confidence=0.9
        ),
        lambda: (_ for _ in ()).throw(RuntimeError("upstream timeout")),
        saga=saga,
    )

    assert outcome.status == "failed"
    assert "upstream timeout" in outcome.error
    assert order == ["undone"]


def test_nothing_is_registered_for_compensation_until_it_succeeds(_stub_persistence):
    """A compensation for a step that never ran is its own kind of bug."""
    order: list[str] = []
    saga = Saga(run_id="r-1")

    submit(
        request(
            actor="intake-agent", action="write_staging", scope=Scope.STAGING_WRITE, confidence=0.9
        ),
        lambda: (_ for _ in ()).throw(RuntimeError("failed")),
        saga=saga,
        compensate=lambda: order.append("should-not-happen"),
    )

    saga.compensate(reason="test")
    assert order == []


# ── The tools that agents actually call ──────────────────────────────────────


def test_proposing_a_schedule_change_reaches_the_approvals_queue(monkeypatch):
    """The tool has to go through the gate, not around it.

    It did not. `propose_schedule_change` wrote its own document into a
    `proposals` collection and returned; the gate was never called, so the
    proposal was never evaluated by the policy engine and never entered the
    approvals queue the carer decides from. Two mechanisms for one idea, running
    past each other.

    What hid it was the fixture corpus. The Approvals screen had committed sample
    cards, so it looked populated and working; the gap only became visible when
    the sample data was deleted and the screen came up empty against a system
    that had just produced two proposals.
    """
    from vigil.fleet import tools

    approvals: list[dict[str, Any]] = []
    monkeypatch.setattr(
        act, "_request_approval", lambda req, dec: (approvals.append({"req": req, "dec": dec}), "ap-1")[1]
    )
    # If the gate is bypassed, this is what gets written instead — and nothing
    # should reach it, because a clinical change is never auto-allowed.
    written: list[Any] = []
    monkeypatch.setattr(tools, "_write_schedule_change", lambda *a: written.append(a))

    result = tools.propose_schedule_change(
        run_id="r-1",
        medication="Cardiolex",
        to_time="12:00",
        reason="five medications collide at 08:00",
        confidence=0.91,
    )

    assert result["status"] == "awaiting_approval"
    assert result["approval_id"] == "ap-1"
    assert written == [], "a clinical change must never be applied without a human"

    assert len(approvals) == 1
    request_made = approvals[0]["req"]
    assert request_made.actor == "meds-agent"
    assert request_made.scope is Scope.SCHEDULE_WRITE
    assert request_made.payload["medication"] == "Cardiolex"
    # The rule that stopped it is the one a person should be shown.
    assert approvals[0]["dec"].rule_id == "approve.clinical"


def test_confidence_reaches_the_gate_rather_than_being_assumed():
    """The number the agent reports is the number the policy engine judges."""
    from vigil.fleet import tools

    seen: list[ActionRequest] = []
    original = act.evaluate

    def spy(req: ActionRequest):
        seen.append(req)
        return original(req)

    act.evaluate = spy
    try:
        tools.propose_schedule_change(
            run_id="r-1", medication="Ferrogen", to_time="14:00", reason="absorption", confidence=0.42
        )
    finally:
        act.evaluate = original

    assert seen and seen[0].confidence == 0.42
