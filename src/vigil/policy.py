"""The policy engine: may this action happen unattended?

Rules are ordered and the first match wins. The ordering is the design, not an
implementation detail, so it is worth being explicit about why it is this way:

    1-2  hard rules      — a property of the action itself
    3-5  soft rules      — a property of how the agent feels about it
    6    default

Hard rules come first specifically so that confidence cannot buy a way past
them. An agent that is certain about a medication change is exactly the agent
you least want acting alone, because certainty is what a confident hallucination
feels like from the inside. No score gets to override a clinical gate.

Every decision carries the id of the rule that produced it. "Denied" is not a
useful audit entry; "denied by deny.unscoped" is something an auditor can argue
with, and something an engineer can find in the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from vigil.fleet.registry import lookup
from vigil.fleet.scopes import EXTERNAL_EFFECT, SCOPE_OWNER, Department, Scope
from vigil.telemetry import log

_log = log("vigil.policy")

#: Below this, an agent's own uncertainty is enough to involve a human.
CONFIDENCE_FLOOR = 0.75


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Verdict(StrEnum):
    AUTO_ALLOW = "auto_allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(slots=True, frozen=True)
class ActionRequest:
    run_id: str
    actor: str
    action: str
    scope: Scope
    confidence: float
    risk: Risk = Risk.LOW
    payload: dict | None = None


@dataclass(slots=True, frozen=True)
class PolicyDecision:
    verdict: Verdict
    rule_id: str
    reason: str

    @property
    def needs_human(self) -> bool:
        return self.verdict is Verdict.REQUIRE_APPROVAL

    @property
    def blocked(self) -> bool:
        return self.verdict is Verdict.DENY


def evaluate(request: ActionRequest) -> PolicyDecision:
    """Decide, and say which rule decided."""
    entry = lookup(request.actor)
    owner = SCOPE_OWNER.get(request.scope)

    # ── Hard rules: about the action, not about the agent ────────────────────

    # 1. The agent does not hold this capability at all. The toolbelt should
    #    already have stopped this; if we are here, something upstream is wrong
    #    and the safe reading is that we cannot trust the request.
    if not entry.holds(request.scope):
        return _decide(
            request,
            Verdict.DENY,
            "deny.unscoped",
            f"{request.actor} does not hold {request.scope.value}",
        )

    # 2. Anything touching clinical data goes to a human. Always. This rule sits
    #    above the confidence rules on purpose — see the module docstring.
    if owner is Department.CLINICAL:
        return _decide(
            request,
            Verdict.REQUIRE_APPROVAL,
            "approve.clinical",
            "Clinical changes are never applied unattended, at any confidence",
        )

    # 3. Irreversible outside this system. Sending a form to an insurer cannot be
    #    taken back, and an idempotency key does not help once it has arrived.
    if request.scope in EXTERNAL_EFFECT:
        return _decide(
            request,
            Verdict.REQUIRE_APPROVAL,
            "approve.external",
            "Irreversible effect outside the system",
        )

    # ── Soft rules: about how the agent feels ────────────────────────────────

    if request.risk is Risk.HIGH:
        return _decide(request, Verdict.REQUIRE_APPROVAL, "approve.high_risk", "Risk rated high")

    if request.confidence < CONFIDENCE_FLOOR:
        return _decide(
            request,
            Verdict.REQUIRE_APPROVAL,
            "approve.low_confidence",
            f"Confidence {request.confidence:.2f} is below {CONFIDENCE_FLOOR}",
        )

    return _decide(
        request,
        Verdict.AUTO_ALLOW,
        "allow.default",
        "Reversible, in scope, and the agent is confident",
    )


def _decide(request: ActionRequest, verdict: Verdict, rule_id: str, reason: str) -> PolicyDecision:
    _log.info(
        "policy.decided",
        run_id=request.run_id,
        actor=request.actor,
        action=request.action,
        verdict=str(verdict),
        rule_id=rule_id,
    )
    return PolicyDecision(verdict=verdict, rule_id=rule_id, reason=reason)
