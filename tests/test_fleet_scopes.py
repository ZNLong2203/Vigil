"""Scope enforcement — the property the whole security story rests on.

These run with no cloud, no emulator and no model, because the guarantee has to
hold before any of those exist. If an agent can reach a tool it does not hold,
that is true regardless of which model is answering.

The audit sink is stubbed out: `audit()` writes to Firestore, and asserting on
scope logic should not require a database.
"""

from __future__ import annotations

from typing import Any

import pytest

from vigil.fleet import registry as reg
from vigil.fleet.budget import BudgetExceeded, RunBudget
from vigil.fleet.scopes import EXTERNAL_EFFECT, SCOPE_OWNER, Department, Scope
from vigil.fleet.toolbelt import REPEAT_LIMIT, build_belt, scope_guard
from vigil.fleet.tools import ALL_TOOLS, scope_of


@pytest.fixture(autouse=True)
def _no_firestore(monkeypatch):
    """Capture audit calls instead of writing them."""
    written: list[dict[str, Any]] = []

    def fake_audit(action: str, actor: str, decision: str, **details: Any) -> str:
        written.append({"action": action, "actor": actor, "decision": decision, **details})
        return "test-entry"

    monkeypatch.setattr("vigil.fleet.toolbelt.audit", fake_audit)
    return written


class FakeTool:
    """Stands in for an ADK BaseTool. The guard only reads `.name`."""

    def __init__(self, name: str) -> None:
        self.name = name


def budget(**kw) -> RunBudget:
    return RunBudget(run_id="test-run", **kw)


# ── Layer 1: assembly ────────────────────────────────────────────────────────


def test_every_tool_declares_a_scope():
    """An untagged tool would be silently excluded from every belt. Catch it
    here rather than wondering later why an agent stopped working."""
    untagged = [f.__name__ for f in ALL_TOOLS if scope_of(f) is None]
    assert untagged == []


@pytest.mark.parametrize("entry", reg.FLEET, ids=lambda e: e.name)
def test_belt_contains_only_held_scopes(entry):
    belt = build_belt(entry)
    for tool in belt:
        assert entry.holds(scope_of(tool.func))


def test_orchestrator_holds_no_business_tools():
    """It routes. If it could read a medication graph it would eventually answer
    from one instead of delegating, and the separation would be decorative."""
    belt = build_belt(reg.lookup("orchestrator"))
    names = {t.name for t in belt}
    assert names == {"find_agents"}


def test_watchdog_cannot_act():
    """A verifier that can change the thing it verifies is not a verifier."""
    entry = reg.lookup("watchdog")
    forbidden = {Scope.SCHEDULE_WRITE, Scope.DOC_GENERATE, Scope.STAGING_WRITE}
    assert forbidden.isdisjoint(entry.tool_scopes)


def test_intake_agent_has_no_external_effect():
    entry = reg.lookup("intake-agent")
    assert EXTERNAL_EFFECT.isdisjoint(entry.tool_scopes)


def test_benefits_agent_cannot_reach_clinical_data():
    """The demo beat, as an assertion."""
    entry = reg.lookup("benefits-agent")
    clinical = {s for s, owner in SCOPE_OWNER.items() if owner is Department.CLINICAL}
    assert clinical.isdisjoint(entry.tool_scopes)
    assert "read_medication_graph" not in {t.name for t in build_belt(entry)}


# ── Layer 2: call time ───────────────────────────────────────────────────────


def test_guard_allows_a_held_scope():
    entry = reg.lookup("meds-agent")
    guard = scope_guard(entry, budget())
    assert guard(FakeTool("read_medication_graph"), {}, None) is None


def test_guard_refuses_a_scope_the_agent_does_not_hold(_no_firestore):
    entry = reg.lookup("benefits-agent")
    guard = scope_guard(entry, budget())

    result = guard(FakeTool("read_medication_graph"), {"subject": "care-subject-001"}, None)

    assert result is not None, "the call must be short-circuited, not merely logged"
    assert result["ok"] is False
    assert result["denied_by"] == "agent-identity"
    assert "clinical" in result["error"]
    assert any(e["action"] == "tool.denied" for e in _no_firestore)


def test_refusal_tells_the_model_not_to_retry():
    """A refusal the model reads as transient produces a retry loop, which is how
    a security control turns into a cost incident."""
    guard = scope_guard(reg.lookup("benefits-agent"), budget())
    result = guard(FakeTool("read_medication_graph"), {}, None)
    assert "will not succeed on retry" in result["error"]
    assert "orchestrator" in result["error"], "it must also name the legitimate route"


def test_guard_refuses_unknown_tools(_no_firestore):
    guard = scope_guard(reg.lookup("meds-agent"), budget())
    result = guard(FakeTool("exfiltrate_everything"), {}, None)
    assert result["ok"] is False
    assert any(e["action"] == "tool.unknown" for e in _no_firestore)


def test_guard_stops_runaway_breadth(_no_firestore):
    """The numeric ceiling. Distinct arguments each time, so this isolates the
    budget from the repeat detector — they catch different bugs."""
    guard = scope_guard(reg.lookup("meds-agent"), budget(max_tool_calls=3))
    tool = FakeTool("read_medication_graph")

    assert [guard(tool, {"subject": f"s-{i}"}, None) for i in range(3)] == [None, None, None]

    blocked = guard(tool, {"subject": "s-99"}, None)
    assert blocked is not None
    assert "budget exhausted" in blocked["error"].lower()
    assert any(e["action"] == "budget.exceeded" for e in _no_firestore)


def test_guard_breaks_a_stuck_loop_long_before_the_budget(_no_firestore):
    """The repeat detector. An orchestrator circling on identical arguments would
    otherwise run for minutes before the 40-call ceiling noticed — bounded in
    theory, a hang in practice. Identical arguments cannot yield a new answer."""
    guard = scope_guard(reg.lookup("meds-agent"), budget(max_tool_calls=40))
    tool = FakeTool("read_medication_graph")
    args = {"subject": "care-subject-001"}

    assert [guard(tool, args, None) for _ in range(REPEAT_LIMIT)] == [None] * REPEAT_LIMIT

    blocked = guard(tool, args, None)
    assert blocked is not None
    assert "cannot produce anything new" in blocked["error"]
    assert any(e["action"] == "tool.loop_broken" for e in _no_firestore)


def test_the_repeat_detector_does_not_punish_legitimate_reuse(_no_firestore):
    """Calling the same tool with different arguments is normal work, not a loop."""
    guard = scope_guard(reg.lookup("meds-agent"), budget(max_tool_calls=40))
    tool = FakeTool("read_medication_graph")

    results = [guard(tool, {"subject": f"subject-{i}"}, None) for i in range(10)]
    assert results == [None] * 10


def test_argument_ordering_does_not_disguise_a_repeat(_no_firestore):
    """A model that reorders its keyword arguments is still making the same call."""
    guard = scope_guard(reg.lookup("meds-agent"), budget(max_tool_calls=40))
    tool = FakeTool("propose_schedule_change")

    guard(tool, {"a": 1, "b": 2}, None)
    guard(tool, {"b": 2, "a": 1}, None)
    blocked = guard(tool, {"a": 1, "b": 2}, None)

    assert blocked is not None and "cannot produce anything new" in blocked["error"]


def test_external_effect_is_recorded_before_it_happens(_no_firestore):
    """An auditor asks what the agent tried to do, not only what succeeded."""
    guard = scope_guard(reg.lookup("meds-agent"), budget())
    assert guard(FakeTool("propose_schedule_change"), {}, None) is None
    assert any(e["action"] == "tool.external_effect" for e in _no_firestore)


# ── Budgets ──────────────────────────────────────────────────────────────────


def test_budget_raises_on_each_limit():
    for spend, limit in (
        (lambda b: b.spend_step(99), "max_steps"),
        (lambda b: b.spend_tool_call(99), "max_tool_calls"),
        (lambda b: b.spend_tokens(10**9), "max_tokens_per_run"),
    ):
        with pytest.raises(BudgetExceeded) as exc:
            spend(budget())
        assert exc.value.limit == limit


def test_budgets_are_per_run():
    """Two runs must not be able to spend each other's allowance."""
    a, b = RunBudget(run_id="a"), RunBudget(run_id="b")
    a.spend_tool_call(5)
    assert b.tool_calls == 0


# ── Registry ─────────────────────────────────────────────────────────────────


def test_discovery_hides_agents_the_caller_may_not_call():
    assert [e.name for e in reg.discover("MedicationContext", "orchestrator")] == ["meds-agent"]
    assert reg.discover("MedicationContext", "benefits-agent") == []


def test_discovery_never_answers_with_nothing():
    """An empty result taught the model nothing, so it guessed another input type
    and called again — seven times, in testing, without producing a plan. A tool
    a model cannot see the schema of has to fail informative, not empty."""
    from vigil.fleet.tools import find_agents

    result = find_agents("NoSuchInputType", "orchestrator")

    assert result["matched"] is None
    assert result["agents"], "an unmatched query must still return the catalogue"
    assert "rather than searching again" in result["note"]


def test_discovery_still_respects_the_calling_boundary_when_it_falls_back():
    """The fallback lists what the caller may call — not everything that exists.
    A helpful error must not become a way around the permission model."""
    from vigil.fleet.tools import find_agents

    names = {a["name"] for a in find_agents("NoSuchInputType", "benefits-agent")["agents"]}
    assert names == set(), "benefits-agent may call nothing, and the fallback must agree"


def test_orchestrator_is_the_only_entry_point():
    """Everything else must be reachable only through the router, or the
    budgets and checkpoints it owns can be bypassed."""
    entry_points = [e.name for e in reg.FLEET if not e.callable_by]
    assert entry_points == ["orchestrator"]


def test_runtime_names_are_valid_python_identifiers():
    """ADK requires it, and the published names contain hyphens on purpose."""
    for entry in reg.FLEET:
        assert entry.runtime_name.isidentifier(), entry.name
