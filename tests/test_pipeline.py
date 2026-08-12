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


async def test_a_pdf_never_costs_a_storage_round_trip(harness, monkeypatch):
    """_attachments once fetched every artifact and then discarded the ones that
    were not images or audio — a Cloud Storage call per delegation to learn what
    the filename already said. It also made the offline test suite hang.
    """
    fetched: list[str] = []
    monkeypatch.setattr(pipe, "resolve", lambda uri: (fetched.append(uri), (b"", "text/plain"))[1])

    harness["outputs"]["orchestrator"] = plan("intake-agent")
    await orchestrate({**EVENT, "source_uri": "gs://x/note.pdf"}, RunBudget(run_id="r-1"))

    assert fetched == [], "a PDF must be decided from its name, not by fetching it"


async def test_an_image_is_attached_to_the_agents_message(harness, monkeypatch):
    """Photos and voice notes cannot travel through a tool result — it is JSON on
    the wire. They ride on the message itself."""
    seen: list[list[tuple[bytes, str]] | None] = []

    async def capture(name, prompt, budget, attachments=None, **kw):
        seen.append(attachments)
        return AgentRun(agent=name, run_id=budget.run_id, output=harness["outputs"].get(name))

    monkeypatch.setattr(pipe, "resolve", lambda uri: (b"\x89PNG-bytes", "image/png"))
    monkeypatch.setattr(pipe, "run_agent", capture)

    harness["outputs"]["orchestrator"] = plan("intake-agent")
    await orchestrate({**EVENT, "source_uri": "gs://x/pill-note-01.png"}, RunBudget(run_id="r-1"))

    worker_attachments = seen[1]
    assert worker_attachments == [(b"\x89PNG-bytes", "image/png")]


async def test_a_missing_attachment_does_not_fail_the_run(harness, monkeypatch):
    """The agent still gets the prompt and will say the record does not support a
    claim, which beats losing the whole run to a 404."""

    def boom(uri):
        raise FileNotFoundError(uri)

    monkeypatch.setattr(pipe, "resolve", boom)
    harness["outputs"]["orchestrator"] = plan("intake-agent")

    result = await orchestrate({**EVENT, "source_uri": "gs://x/gone.png"}, RunBudget(run_id="r-1"))

    assert len(result.workers) == 1


async def test_a_tool_audit_is_attributed_to_the_run(harness, monkeypatch):
    """The trust boundary blocks an injected document from inside read_artifact,
    which has no run_id in its signature — tools take what the model needs to
    decide, not our bookkeeping. Without an ambient run the block never appeared
    in that run's trace: the one event the design exists to produce was invisible
    on the screen built to show it.
    """
    from vigil import state

    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(
        state,
        "db",
        lambda: (_ for _ in ()).throw(RuntimeError("no datastore in this test")),
    )
    monkeypatch.setattr(state._log, "info", lambda *a, **k: seen.append(k))
    monkeypatch.setattr(state._log, "error", lambda *a, **k: None)

    async def audits_from_a_tool(name, prompt, budget, **kw):
        # Stands in for read_artifact: deep in the stack, no run_id to hand over.
        state.audit("guardrail.blocked", actor="trust-boundary", decision="blocked")
        return AgentRun(agent=name, run_id=budget.run_id, output=harness["outputs"].get(name))

    monkeypatch.setattr(pipe, "run_agent", audits_from_a_tool)
    harness["outputs"]["orchestrator"] = plan("intake-agent")

    await orchestrate(EVENT, RunBudget(run_id="r-ambient"))

    blocks = [e for e in seen if e.get("action") == "guardrail.blocked"]
    assert blocks, "the tool's audit entry was never written"
    assert blocks[0]["run_id"] == "r-ambient"


def test_an_explicit_run_id_beats_the_ambient_one():
    """The context is a fallback, never an override — an entry that names its run
    means it."""
    from vigil import state

    token = state.set_current_run("r-ambient")
    try:
        seen: list[dict[str, Any]] = []
        original = state._log.info
        state._log.info = lambda *a, **k: seen.append(k)
        try:
            state.db.cache_clear()
            state.audit("x", actor="a", decision="done", run_id="r-explicit")
        finally:
            state._log.info = original
    finally:
        state.reset_current_run(token)

    assert seen[0]["run_id"] == "r-explicit"
