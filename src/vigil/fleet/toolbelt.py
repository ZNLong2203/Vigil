"""Two-layer scope enforcement.

The category asks for agents that touch production data without violating
policy. The honest way to read that requirement is: assume the model will one day
try. A well-phrased document, a confused plan, a prompt that survived the trust
boundary — any of these can end with an agent reaching for something outside its
boundary. The system has to be uninteresting when that happens.

  Layer 1 — assembly (`build_belt`)
      An agent is handed only the tools whose scope its registry entry holds.
      The model never sees a declaration for anything else, so there is nothing
      to call. This stops the ordinary case.

  Layer 2 — call time (`scope_guard`)
      A `before_tool_callback` re-checks the scope on every invocation. Returning
      a dict from that callback short-circuits the tool: the call never runs, the
      model receives a refusal it can reason about, and an audit entry is
      written. This stops the case where layer 1 was wired wrong.

Two layers because layer 1 is a property of our wiring, and wiring changes. The
demo beat — benefits-agent reaching for a clinical note and being refused — is
layer 2 doing its job on camera.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from google.adk.tools import BaseTool, FunctionTool, ToolContext

from vigil.fleet.budget import BudgetExceeded, RunBudget
from vigil.fleet.registry import AgentEntry
from vigil.fleet.scopes import EXTERNAL_EFFECT, SCOPE_OWNER, Scope
from vigil.fleet.tools import ALL_TOOLS, scope_of
from vigil.state import audit
from vigil.telemetry import log

_log = log("vigil.toolbelt")


def build_belt(entry: AgentEntry) -> list[FunctionTool]:
    """Layer 1. Only the tools this agent's registry entry authorises.

    A tool with no scope tag is excluded rather than allowed — failing closed is
    the only safe default for the component whose job is limiting blast radius.
    """
    belt: list[FunctionTool] = []
    for func in ALL_TOOLS:
        scope = scope_of(func)
        if scope is None:
            _log.warning("tool.untagged", tool=func.__name__, action="excluded")
            continue
        if entry.holds(scope):
            belt.append(FunctionTool(func))

    _log.info(
        "toolbelt.built",
        agent=entry.name,
        tools=[t.name for t in belt],
        scopes=[str(s) for s in entry.tool_scopes],
    )
    return belt


def _scope_index() -> dict[str, Scope]:
    """Tool name → required scope, so the guard can decide from the name alone."""
    return {func.__name__: scope for func in ALL_TOOLS if (scope := scope_of(func))}


#: How many times an agent may make the *same* call with the *same* arguments
#: before the guard answers instead of the tool.
REPEAT_LIMIT = 2


def scope_guard(
    entry: AgentEntry,
    budget: RunBudget,
) -> Callable[[BaseTool, dict[str, Any], ToolContext], dict[str, Any] | None]:
    """Layer 2. A `before_tool_callback` that refuses out-of-scope calls, and
    breaks the loop when an agent stops making progress.

    Returning None lets the call proceed; returning a dict replaces the tool's
    result with that dict and the tool never runs.

    The repeat detector exists because the numeric budget is the wrong shape for
    this failure. An orchestrator that got stuck calling `find_agents` with
    identical arguments would have run for thirteen minutes before the 40-call
    ceiling caught it — technically bounded, practically a hang, and expensive
    the whole way. Identical arguments cannot produce a new answer, so the
    second repeat is already enough evidence: the agent is not progressing, it is
    circling. Counting distinct calls catches runaway breadth; counting repeats
    catches a stuck loop, and they are different bugs.
    """
    index = _scope_index()
    seen: dict[tuple[str, str], int] = {}

    def guard(
        tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
    ) -> dict[str, Any] | None:
        required = index.get(tool.name)

        # An unknown tool is a wiring bug, and a wiring bug in this component is
        # exactly what layer 2 exists to catch. Refuse rather than guess.
        if required is None:
            audit(
                "tool.unknown",
                actor=entry.name,
                decision="denied",
                tool=tool.name,
                run_id=budget.run_id,
            )
            return {
                "ok": False,
                "error": f"{tool.name!r} is not a registered tool. Do not retry it.",
            }

        if not entry.holds(required):
            owner = SCOPE_OWNER.get(required)
            boundary = str(owner) if owner else "infrastructure"
            audit(
                "tool.denied",
                actor=entry.name,
                decision="denied",
                tool=tool.name,
                required_scope=str(required),
                boundary=boundary,
                run_id=budget.run_id,
            )
            _log.warning(
                "scope.denied",
                agent=entry.name,
                tool=tool.name,
                required=str(required),
                boundary=boundary,
            )
            # The refusal is phrased for the model, not for a log reader: it has
            # to understand that retrying is pointless and that a legitimate
            # route exists.
            return {
                "ok": False,
                "denied_by": "agent-identity",
                "error": (
                    f"Denied. {tool.name!r} requires {required.value}, which belongs to the "
                    f"{boundary} boundary and is not held by {entry.name}. This will not "
                    f"succeed on retry. If you need this information, ask the orchestrator "
                    f"to route the request to the agent that owns it."
                ),
            }

        signature = (tool.name, json.dumps(args, sort_keys=True, default=str))
        seen[signature] = seen.get(signature, 0) + 1
        if seen[signature] > REPEAT_LIMIT:
            audit(
                "tool.loop_broken",
                actor=entry.name,
                decision="denied",
                tool=tool.name,
                repeats=seen[signature],
                run_id=budget.run_id,
            )
            _log.warning("loop.broken", agent=entry.name, tool=tool.name, repeats=seen[signature])
            # Phrased so the model treats it as a fact about its own behaviour
            # rather than a transient tool failure to route around.
            return {
                "ok": False,
                "error": (
                    f"You have already called {tool.name!r} with these exact arguments "
                    f"{seen[signature] - 1} times and received the same answer each time. "
                    f"Calling it again cannot produce anything new. Stop using this tool "
                    f"and give your final answer from what you already have. If you cannot, "
                    f"say what is missing."
                ),
            }

        try:
            budget.spend_tool_call()
        except BudgetExceeded as exc:
            audit(
                "budget.exceeded",
                actor=entry.name,
                decision="failed",
                limit=exc.limit,
                used=exc.used,
                cap=exc.cap,
                run_id=budget.run_id,
            )
            return {
                "ok": False,
                "error": (
                    f"Tool budget exhausted for this run ({exc.used}/{exc.cap}). "
                    f"Stop calling tools and return your best answer from what you have."
                ),
            }

        if required in EXTERNAL_EFFECT:
            # Not a block — these tools only ever create proposals. Recording the
            # intent separately means the audit trail shows what the agent
            # *wanted*, which is what an auditor actually asks about.
            audit(
                "tool.external_effect",
                actor=entry.name,
                decision="accepted",
                tool=tool.name,
                run_id=budget.run_id,
            )

        return None

    return guard
