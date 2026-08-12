"""Running an agent, and recording what it did while it ran.

The ADK runner yields a stream of events. Draining that stream and keeping only
the final answer would throw away the interesting part: which tools were called,
which calls the scope guard refused, what each hop cost. That trace is what the
reasoning-chain view renders and what an auditor asks for, so it is collected
here rather than reconstructed from logs afterwards.

Token accounting is charged to the run's budget as it arrives, not at the end.
A run that blows its ceiling mid-flight needs to stop mid-flight; discovering it
afterwards is just a bill.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from google.adk.runners import InMemoryRunner
from google.genai import types

from vigil.fleet.agents import build_agent
from vigil.fleet.budget import BudgetExceeded, RunBudget
from vigil.telemetry import log, span

_log = log("vigil.run")

APP_NAME = "vigil"


@dataclass(slots=True)
class ToolCall:
    name: str
    args: dict[str, Any]
    response: dict[str, Any] | None = None

    @property
    def denied(self) -> bool:
        """True when the scope guard refused this call rather than the tool
        failing on its own. The distinction matters: one is a policy event worth
        surfacing, the other is a bad day for a dependency."""
        return bool(self.response and self.response.get("denied_by"))


@dataclass(slots=True)
class AgentRun:
    agent: str
    run_id: str
    output: Any = None
    raw_text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    elapsed_s: float = 0.0
    stopped_by: str | None = None

    @property
    def denials(self) -> list[ToolCall]:
        return [c for c in self.tool_calls if c.denied]

    def summary(self) -> str:
        parts = [
            f"{self.agent}: {len(self.tool_calls)} tool calls, "
            f"{self.tokens} tokens, {self.elapsed_s}s"
        ]
        if self.denials:
            parts.append(f"{len(self.denials)} denied")
        if self.stopped_by:
            parts.append(f"stopped by {self.stopped_by}")
        return " · ".join(parts)


async def run_agent(
    name: str,
    prompt: str,
    budget: RunBudget,
    *,
    user_id: str = "vigil-system",
) -> AgentRun:
    """Run one agent to completion and return what it produced and what it did.

    Raises nothing on a budget breach: the run comes back with `stopped_by` set
    and whatever partial output exists. A ceiling is a normal outcome, not an
    exception — the caller decides whether a truncated plan is still usable.
    """
    agent = build_agent(name, budget)
    result = AgentRun(agent=name, run_id=budget.run_id)

    runner = InMemoryRunner(agent=agent, app_name=APP_NAME)
    session_id = f"{budget.run_id}-{uuid.uuid4().hex[:8]}"
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    pending: dict[str, ToolCall] = {}
    started = time.monotonic()

    with span("agent.run", agent=name, run_id=budget.run_id, model=str(agent.model)):
        try:
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=message
            ):
                if usage := getattr(event, "usage_metadata", None):
                    if total := getattr(usage, "total_token_count", None):
                        result.tokens += total
                        budget.spend_tokens(total)

                for call in event.get_function_calls() or []:
                    record = ToolCall(name=call.name, args=dict(call.args or {}))
                    result.tool_calls.append(record)
                    if call.id:
                        pending[call.id] = record
                    # Emitted as it happens rather than at the end. A step that
                    # takes half a minute is normal here; a silent half minute
                    # is what makes people kill a working process.
                    _log.info(
                        "run.tool_called",
                        agent=name,
                        run_id=budget.run_id,
                        tool=call.name,
                        elapsed_s=round(time.monotonic() - started, 1),
                    )

                for response in event.get_function_responses() or []:
                    payload = response.response
                    if not isinstance(payload, dict):
                        payload = {"value": payload}
                    if record := pending.pop(response.id or "", None):
                        record.response = payload
                    elif result.tool_calls:
                        # Some model versions omit call ids; the last unanswered
                        # call is the only sensible owner.
                        result.tool_calls[-1].response = payload

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            result.raw_text = part.text

        except BudgetExceeded as exc:
            result.stopped_by = exc.limit
            _log.warning(
                "run.budget_exceeded",
                agent=name,
                run_id=budget.run_id,
                limit=exc.limit,
                used=exc.used,
            )
        except Exception as exc:
            if _is_daily_quota(exc):
                # Transport retry cannot help here and trying only spends the
                # quota that is already gone. Surface it as its own outcome so an
                # operator reads "come back tomorrow or enable billing" rather
                # than "the fleet is broken".
                result.stopped_by = "daily_quota"
                _log.error(
                    "run.daily_quota_exhausted",
                    agent=name,
                    run_id=budget.run_id,
                    model=str(agent.model),
                    note="free tier is 20 requests/day/model; retrying will not help",
                )
            else:
                raise
        finally:
            await runner.close()

    result.output = _parse(name, result.raw_text)
    result.elapsed_s = round(time.monotonic() - started, 1)
    _log.info("run.finished", agent=name, run_id=budget.run_id, summary=result.summary())
    return result


def _is_daily_quota(exc: BaseException) -> bool:
    """Tell a per-day quota breach apart from a per-minute one.

    Both arrive as 429 and the transport layer cannot distinguish them, so it
    backs off and retries either way. For a per-minute limit that is right. For a
    per-day limit every attempt is a request that will fail, spending the
    allowance it is waiting for — six retries can burn a third of a free tier's
    daily budget discovering that the daily budget is gone.

    The quotaId is the only thing that separates them:
        GenerateRequestsPerMinutePerProjectPerModel-FreeTier   retry
        GenerateRequestsPerDayPerProjectPerModel-FreeTier      stop
    """
    text = str(exc)
    return "PerDay" in text or "per day" in text.lower()


def _parse(name: str, text: str) -> Any:
    """Validate the final text against the agent's declared output schema.

    A parse failure is returned as None rather than raised. The trace is still
    worth having — knowing an agent produced 900 tokens of unparseable output is
    more useful than losing the evidence to an exception.
    """
    from vigil.fleet.agents import OUTPUT_SCHEMA

    schema = OUTPUT_SCHEMA.get(name)
    if not schema or not text.strip():
        return None
    try:
        return schema.model_validate_json(text)
    except Exception as exc:
        _log.warning("run.unparseable_output", agent=name, error=str(exc)[:200])
        return None
