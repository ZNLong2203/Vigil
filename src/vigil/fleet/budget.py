"""Per-run budgets — the loop breaker.

An agent that loops is not a cost problem first, it is a correctness problem: it
means the plan stopped converging and nothing noticed. The budget is the thing
that notices.

Three counters rather than one, because the three failure shapes are different:

  steps       the orchestrator keeps re-planning without progressing
  tool_calls  a worker retries the same tool against a broken dependency
  tokens      a single call ran away on a pathological input

Exceeding any of them aborts the run and writes an audit entry. It never fails
silently, because a silently truncated run looks identical to a successful one.

This is also layer 1 of the cost defence described in the README; layers 2 and 3
are Cloud Run --max-instances and billing budget alerts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vigil.config import get_settings
from vigil.telemetry import log

_log = log("vigil.budget")


class BudgetExceeded(Exception):
    """Raised when a run hits a ceiling. Terminal for that run, not for the fleet."""

    def __init__(self, run_id: str, limit: str, used: int, cap: int) -> None:
        self.run_id = run_id
        self.limit = limit
        self.used = used
        self.cap = cap
        super().__init__(f"run {run_id} exceeded {limit}: {used} > {cap}")


@dataclass(slots=True)
class RunBudget:
    """Mutable counters for one run. Not shared across runs — a noisy neighbour
    must not be able to starve an unrelated care workflow."""

    run_id: str
    max_steps: int = field(default=0)
    max_tool_calls: int = field(default=0)
    max_tokens: int = field(default=0)

    steps: int = 0
    tool_calls: int = 0
    tokens: int = 0

    def __post_init__(self) -> None:
        s = get_settings()
        self.max_steps = self.max_steps or s.max_steps
        self.max_tool_calls = self.max_tool_calls or s.max_tool_calls
        self.max_tokens = self.max_tokens or s.max_tokens_per_run

    def spend_step(self, n: int = 1) -> None:
        self.steps += n
        if self.steps > self.max_steps:
            raise BudgetExceeded(self.run_id, "max_steps", self.steps, self.max_steps)

    def spend_tool_call(self, n: int = 1) -> None:
        self.tool_calls += n
        if self.tool_calls > self.max_tool_calls:
            raise BudgetExceeded(
                self.run_id, "max_tool_calls", self.tool_calls, self.max_tool_calls
            )

    def spend_tokens(self, n: int) -> None:
        self.tokens += n
        if self.tokens > self.max_tokens:
            raise BudgetExceeded(self.run_id, "max_tokens_per_run", self.tokens, self.max_tokens)

    @property
    def remaining_steps(self) -> int:
        return max(0, self.max_steps - self.steps)

    def snapshot(self) -> dict[str, int]:
        return {
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "tokens": self.tokens,
            "max_steps": self.max_steps,
            "max_tool_calls": self.max_tool_calls,
            "max_tokens": self.max_tokens,
        }

    def log_state(self) -> None:
        _log.info("budget.state", run_id=self.run_id, **self.snapshot())
