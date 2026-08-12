"""One event, through the whole fleet.

    orchestrator plans → workers act → watchdog verifies → escalate or finish

Three things make this more than a for-loop over agents.

**Every hop is a checkpointed step.** Not for elegance: an agent hop costs 10-30
seconds and a Cloud Run instance can be replaced mid-flight. Without a checkpoint
per hop, a redelivery re-runs the whole chain from the top and pays for it twice.
With one, a resumed run skips what already happened — the same idempotency
machinery that stops a duplicate benefits filing also stops a duplicate LLM bill.

**The budget is shared across the chain, not per agent.** A run that spends its
whole allowance on planning has nothing left to verify with, and the honest
outcome is a truncated run that says so — not three agents that each stayed
politely under their own limit while the run as a whole ran away.

**The watchdog runs last and can override.** A verified-false verdict does not
delete the work; it escalates it with the reasoning attached. An agent that
cannot be overruled is not supervised.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import mimetypes
import os
from dataclasses import dataclass, field
from typing import Any

from vigil.fleet.budget import RunBudget
from vigil.fleet.registry import lookup
from vigil.fleet.run import AgentRun, run_agent
from vigil.state import (
    StepAlreadyDone,
    audit,
    claim_step,
    complete_step,
    fail_step,
    reset_current_run,
    set_current_run,
)
from vigil.storage import resolve
from vigil.telemetry import log, span

_log = log("vigil.pipeline")

#: Hard ceiling on delegations honoured from one plan. The orchestrator is
#: instructed to delegate narrowly; this is what happens when it does not.
MAX_DELEGATIONS = 3


@dataclass(slots=True)
class PipelineResult:
    run_id: str
    plan: AgentRun | None = None
    workers: list[AgentRun] = field(default_factory=list)
    verdict: AgentRun | None = None
    escalated: bool = False
    stopped_by: str | None = None

    @property
    def agent_runs(self) -> list[AgentRun]:
        return [r for r in [self.plan, *self.workers, self.verdict] if r]

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens for r in self.agent_runs)

    @property
    def denials(self) -> list[Any]:
        return [call for r in self.agent_runs for call in r.denials]

    def summary(self) -> str:
        parts = [
            f"{len(self.agent_runs)} agents",
            f"{self.total_tokens} tokens",
            f"{sum(r.elapsed_s for r in self.agent_runs):.1f}s",
        ]
        if self.denials:
            parts.append(f"{len(self.denials)} boundary denials")
        if self.escalated:
            parts.append("escalated")
        if self.stopped_by:
            parts.append(f"stopped by {self.stopped_by}")
        return " · ".join(parts)


async def orchestrate(event: dict[str, Any], budget: RunBudget) -> PipelineResult:
    """Run one event through the fleet."""
    run_id = budget.run_id
    result = PipelineResult(run_id=run_id)

    # Everything below — including tools called by the model, which have no way
    # to know the run — records against this run.
    token = set_current_run(run_id)
    try:
        return await _orchestrate(event, budget, result)
    finally:
        reset_current_run(token)


async def _orchestrate(
    event: dict[str, Any], budget: RunBudget, result: PipelineResult
) -> PipelineResult:
    run_id = budget.run_id

    with span("pipeline.orchestrate", run_id=run_id, kind=event.get("kind")):
        # ── Plan ─────────────────────────────────────────────────────────────
        result.plan = await _step(run_id, "plan", "orchestrator", _plan_prompt(event), budget)
        if result.plan is None:
            result.stopped_by = "plan_step_replayed"
            return result
        if result.plan.stopped_by:
            result.stopped_by = result.plan.stopped_by
            return result

        plan = result.plan.output
        if plan is None:
            # A plan that will not parse is not a plan. Escalating beats guessing
            # at what the orchestrator meant.
            audit("plan.unparseable", actor="orchestrator", decision="escalated", run_id=run_id)
            result.escalated = True
            return result

        if not plan.delegations:
            audit(
                "plan.no_action",
                actor="orchestrator",
                decision="done",
                run_id=run_id,
                reason=plan.stop_reason or "nothing to do",
            )
            return result

        # ── Delegate ─────────────────────────────────────────────────────────
        for index, delegation in enumerate(plan.delegations[:MAX_DELEGATIONS]):
            try:
                entry = lookup(delegation.agent)
            except KeyError:
                # The orchestrator named an agent that does not exist. That is a
                # hallucination with a plan attached, and the registry is the
                # only thing standing between it and a real call.
                audit(
                    "delegation.unknown_agent",
                    actor="orchestrator",
                    decision="denied",
                    run_id=run_id,
                    requested=delegation.agent,
                )
                continue

            if not entry.may_be_called_by("orchestrator"):
                audit(
                    "delegation.not_permitted",
                    actor="orchestrator",
                    decision="denied",
                    run_id=run_id,
                    requested=delegation.agent,
                )
                continue

            worker = await _step(
                run_id,
                f"delegate-{index}-{entry.name}",
                entry.name,
                _worker_prompt(event, delegation),
                budget,
                attachments=_attachments(event),
            )
            if worker is None:
                continue
            result.workers.append(worker)
            if worker.stopped_by:
                result.stopped_by = worker.stopped_by
                break

        # ── Verify ───────────────────────────────────────────────────────────
        if result.workers and not result.stopped_by:
            result.verdict = await _step(
                run_id, "verify", "watchdog", _verify_prompt(event, result.workers), budget
            )
            verdict = result.verdict.output if result.verdict else None
            if verdict and (verdict.escalate or not verdict.verified):
                result.escalated = True
                audit(
                    "watchdog.escalated",
                    actor="watchdog",
                    decision="escalated",
                    run_id=run_id,
                    unsupported=len(verdict.unsupported_claims),
                    contradictions=len(verdict.contradictions),
                )

    _log.info("pipeline.finished", run_id=run_id, summary=result.summary())
    return result


async def _step(
    run_id: str,
    step_id: str,
    agent: str,
    prompt: str,
    budget: RunBudget,
    *,
    attachments: list[tuple[bytes, str]] | None = None,
) -> AgentRun | None:
    """One agent hop, guarded by the same checkpoint machinery as any side effect.

    Returns None when the step was already done — a redelivery, not a failure.
    """
    payload = {"agent": agent, "prompt_digest": _stable_digest(prompt)}
    try:
        key = claim_step(run_id, step_id, payload)
    except StepAlreadyDone:
        audit("agent.step_replayed", actor=agent, decision="skipped", run_id=run_id, step=step_id)
        return None

    # Demo affordance, off unless explicitly set. This is the exact window the
    # design turns on — the claim is held, the work has not happened — so it is
    # the window `make chaos` has to kill the process inside. Real agent work
    # occupies it for 10-30 seconds on its own; the delay only makes the moment
    # reproducible on camera.
    delay_ms = int(os.environ.get("VIGIL_DEMO_DELAY_MS", "0"))
    if delay_ms:
        _log.info(
            "demo.delay",
            run_id=run_id,
            step=step_id,
            ms=delay_ms,
            note="claim held, work not yet done — safe to kill now",
        )
        await asyncio.sleep(delay_ms / 1000)

    try:
        run = await run_agent(agent, prompt, budget, attachments=attachments)
    except Exception as exc:
        fail_step(run_id, step_id, key, str(exc))
        audit("agent.failed", actor=agent, decision="failed", run_id=run_id, error=str(exc)[:200])
        raise

    complete_step(
        run_id,
        step_id,
        key,
        {
            "tokens": run.tokens,
            "elapsed_s": run.elapsed_s,
            "tools": len(run.tool_calls),
            # What the agent actually concluded, not only what it cost.
            #
            # The checkpoint stored the meter readings and threw the work away.
            # Nothing downstream could answer "what did the agent understand from
            # this photograph" — which is the entire argument of the Intake
            # screen, the pairing of a messy input with the structured reading of
            # it. That screen filled the gap with authored examples, so the
            # missing half looked like a design choice rather than lost data.
            "output": _serialisable(run.output),
        },
    )
    budget.spend_step()
    return run


#: Firestore rejects a document over 1 MiB, and a checkpoint is written on a
#: path where failing is expensive — the agent has already done the work. Well
#: under the limit rather than near it.
_MAX_OUTPUT_CHARS = 20_000


def _serialisable(output: Any) -> dict[str, Any] | None:
    """The agent's structured output, as something Firestore will accept.

    Returns None rather than raising: a checkpoint that fails to write turns a
    completed hop into a repeated one, and no screen is worth paying for a step
    twice.
    """
    if output is None:
        return None
    try:
        data = output.model_dump(mode="json") if hasattr(output, "model_dump") else dict(output)
        if len(json.dumps(data)) > _MAX_OUTPUT_CHARS:
            return {"truncated": True, "summary": str(getattr(output, "summary", ""))[:500]}
        return data
    except Exception as exc:  # noqa: BLE001 — see docstring
        _log.warning("checkpoint.output_unserialisable", error=str(exc)[:200])
        return None


def _attachments(event: dict[str, Any]) -> list[tuple[bytes, str]]:
    """Load a photo or voice note so it travels with the agent's message.

    Only binaries. A PDF stays on the tool path, because its text has to cross
    the trust boundary first — attaching one directly would route an injected
    document straight into the prompt, past the screen that exists to catch it.

    A missing artifact returns nothing rather than raising: the agent still gets
    the prompt and will say the record does not support a claim, which is a
    better outcome than a failed run.
    """
    source_uri = event.get("source_uri")
    if not source_uri:
        return []

    # Decide from the name before fetching anything. Fetching first and then
    # discarding non-binaries meant every PDF delegation paid for a Cloud Storage
    # round-trip to learn it was a PDF — latency and cost on the hot path, for an
    # answer already visible in the filename.
    guessed = mimetypes.guess_type(source_uri)[0] or ""
    if not guessed.startswith(("image/", "audio/")):
        return []

    try:
        data, content_type = resolve(source_uri)
    except Exception as exc:
        _log.warning("attachment.unavailable", source_uri=source_uri, error=str(exc)[:120])
        return []

    if not content_type.startswith(("image/", "audio/")):
        return []

    _log.info(
        "attachment.loaded", source_uri=source_uri, content_type=content_type, bytes=len(data)
    )
    return [(data, content_type)]


def _stable_digest(text: str) -> str:
    """Python's hash() is salted per process, so a resumed run in a new process
    would compute a different idempotency payload for the same prompt and claim
    the step again. That is the whole failure this design exists to prevent —
    see ADR 002 and tests/test_idempotency.py."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ── Prompts ──────────────────────────────────────────────────────────────────
#
# Kept here rather than in agents.py because these are *per-run* context, while
# the instructions in agents.py are the agent's standing character. Mixing the
# two is how a system prompt slowly fills up with details of one event.


def _plan_prompt(event: dict[str, Any]) -> str:
    return (
        f"An event arrived for care subject {event.get('subject', 'unknown')}.\n\n"
        f"kind: {event.get('kind')}\n"
        f"source_uri: {event.get('source_uri') or '(none)'}\n"
        f"body: {json.dumps(event.get('body', {}), indent=2)}\n\n"
        "Decide who should handle it. Remember you cannot read the document "
        "yourself — decide from what the event says about itself."
    )


def _worker_prompt(event: dict[str, Any], delegation: Any) -> str:
    return (
        f"The orchestrator delegated this to you: {delegation.reason}\n\n"
        f"subject: {event.get('subject')}\n"
        f"source_uri: {event.get('source_uri') or '(none)'}\n"
        f"context: {delegation.input_summary}\n\n"
        "Do your part and nothing else. If the work needs a capability you do "
        "not hold, say so rather than working around it."
    )


def _verify_prompt(event: dict[str, Any], workers: list[AgentRun]) -> str:
    reports = "\n\n".join(
        f"--- {w.agent} (run {w.run_id}) ---\n{w.raw_text[:3000]}" for w in workers
    )
    return (
        f"Verify the following agent output for subject {event.get('subject')}, "
        f"run {workers[0].run_id}.\n\n{reports}\n\n"
        "Check each claim against the persisted record. Report contradictions "
        "without resolving them. Escalate if a human needs to decide."
    )
