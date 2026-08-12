"""Routing between agents, without calling a model.

The interesting failures here are not model failures. They are the orchestrator
naming an agent that does not exist, naming one it is not allowed to call, or
returning a plan with twenty delegations in it. Each of those is a plausible
model output and each has to be survivable, so each is asserted here with the
model stubbed out entirely.
"""

from __future__ import annotations

from typing import Any

import pytest

from vigil.fleet import pipeline as pipe
from vigil.fleet.budget import RunBudget
from vigil.fleet.pipeline import MAX_DELEGATIONS, orchestrate
from vigil.fleet.run import AgentRun
from vigil.fleet.schemas import Delegation, RunPlan

EVENT = {
    "run_id": "r-1",
    "kind": "document",
    "subject": "care-subject-001",
    "source_uri": "gs://x/care-note-week3.pdf",
    "body": {},
}


@pytest.fixture()
def harness(monkeypatch):
    """Stub the model and the datastore; record what was asked of each agent."""
    calls: list[str] = []
    trail: list[dict[str, Any]] = []
    outputs: dict[str, Any] = {}
    claimed: set[tuple[str, str]] = set()

    async def fake_run_agent(name, prompt, budget, **kw):
        calls.append(name)
        return AgentRun(agent=name, run_id=budget.run_id, output=outputs.get(name), tokens=10)

    def fake_claim(run_id, step_id, payload):
        if (run_id, step_id) in claimed:
            raise pipe.StepAlreadyDone("already")
        claimed.add((run_id, step_id))
        return f"key-{step_id}"

    monkeypatch.setattr(pipe, "run_agent", fake_run_agent)
    monkeypatch.setattr(pipe, "claim_step", fake_claim)
    monkeypatch.setattr(pipe, "complete_step", lambda *a, **k: None)
    monkeypatch.setattr(pipe, "fail_step", lambda *a, **k: None)
    monkeypatch.setattr(
        pipe,
        "audit",
        lambda action, actor, decision, **d: (
            trail.append({"action": action, "actor": actor, "decision": decision, **d}) or "e"
        ),
    )
    return {"calls": calls, "trail": trail, "outputs": outputs, "claimed": claimed}


def plan(*agents: str) -> RunPlan:
    return RunPlan(
        intent="handle the document",
        delegations=[
            Delegation(agent=a, reason="because", input_summary="the document") for a in agents
        ],
    )


async def test_happy_path_plans_delegates_and_verifies(harness):
    harness["outputs"]["orchestrator"] = plan("intake-agent")

    result = await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert harness["calls"] == ["orchestrator", "intake-agent", "watchdog"]
    assert len(result.workers) == 1


async def test_a_hallucinated_agent_name_is_refused(harness):
    """The registry is the only thing between a plan and a real call."""
    harness["outputs"]["orchestrator"] = plan("totally-made-up-agent")

    await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert harness["calls"] == ["orchestrator"], "the fake agent must never be invoked"
    assert any(e["action"] == "delegation.unknown_agent" for e in harness["trail"])


async def test_delegating_to_an_agent_the_orchestrator_may_not_call_is_refused(harness):
    """watchdog lists orchestrator in callable_by; orchestrator itself does not
    list anyone, so it is not delegatable — a plan naming it is a routing loop."""
    harness["outputs"]["orchestrator"] = plan("orchestrator")

    await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert harness["calls"] == ["orchestrator"]
    assert any(e["action"] == "delegation.not_permitted" for e in harness["trail"])


async def test_an_over_eager_plan_is_capped(harness):
    harness["outputs"]["orchestrator"] = plan(
        *(["intake-agent", "meds-agent", "benefits-agent"] * 4)
    )

    result = await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert len(result.workers) == MAX_DELEGATIONS


async def test_an_empty_plan_does_nothing_and_says_so(harness):
    """Doing nothing is a valid outcome. It must not look like a failure."""
    harness["outputs"]["orchestrator"] = RunPlan(
        intent="nothing needed", delegations=[], stop_reason="already handled last week"
    )

    result = await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert harness["calls"] == ["orchestrator"]
    assert result.workers == []
    assert result.escalated is False
    assert any(e["action"] == "plan.no_action" for e in harness["trail"])


async def test_an_unparseable_plan_escalates_rather_than_guessing(harness):
    harness["outputs"]["orchestrator"] = None  # schema validation failed upstream

    result = await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert result.escalated is True
    assert harness["calls"] == ["orchestrator"]


async def test_a_redelivered_event_does_not_re_run_the_chain(harness):
    """The expensive half of exactly-once: a replay must not pay for the agents
    a second time."""
    harness["outputs"]["orchestrator"] = plan("intake-agent")
    budget = RunBudget(run_id="r-1")

    await orchestrate(EVENT, budget)
    first = list(harness["calls"])
    harness["calls"].clear()

    await orchestrate(EVENT, RunBudget(run_id="r-1"))

    assert first == ["orchestrator", "intake-agent", "watchdog"]
    assert harness["calls"] == [], "a redelivery must call no agents at all"


def test_the_step_digest_survives_a_process_restart():
    """Python salts hash() per process, so an idempotency payload built from it
    changes every time the worker restarts — and a resumed run would claim a step
    it had already completed and pay for the agent twice. Resume happens in a new
    process by definition, so this has to be checked in one."""
    import subprocess
    import sys

    from vigil.fleet.pipeline import _stable_digest

    code = (
        "import sys; sys.path.insert(0, 'src');"
        "from vigil.fleet.pipeline import _stable_digest;"
        "print(_stable_digest('the same prompt'))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == _stable_digest("the same prompt")


async def test_the_budget_is_shared_across_the_whole_chain(harness):
    """Per-agent budgets would let a three-hop run spend three times the ceiling
    while every agent stayed politely under its own."""
    harness["outputs"]["orchestrator"] = plan("intake-agent", "meds-agent")
    budget = RunBudget(run_id="r-1")

    await orchestrate(EVENT, budget)

    assert budget.steps == 4, "plan + 2 workers + verify"


def test_runtime_imports_are_not_dev_dependencies():
    """`uv sync --no-dev` builds the container, so anything src/ imports at
    runtime must be a project dependency. pypdf was a dev dependency once: the
    image shipped without it, read_artifact could not open a PDF, and the only
    reason it surfaced was the watchdog escalating in production.
    """
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    runtime = {
        dep.split(">")[0].split("[")[0].strip() for dep in pyproject["project"]["dependencies"]
    }

    # Imported lazily inside tool functions, so a missing one fails at call time
    # rather than at import — which is exactly why it needs asserting here.
    for module in ("pypdf", "python-dotenv"):
        assert module in runtime, f"{module} must be a runtime dependency, not a dev one"
