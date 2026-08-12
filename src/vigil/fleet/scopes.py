"""Tool scopes and department boundaries.

The category asks for agents that "interact with production data without
violating compliance, data sovereignty, or security policies". An instruction
telling an agent not to read something is not a policy — it is a request, and a
sufficiently confused model will talk itself out of it.

So a scope here is a capability the agent either holds or does not. It is
enforced twice:

  1. at assembly, in toolbelt.build_belt — an agent is never handed a tool whose
     scope it does not hold, so the model cannot see it to call it;
  2. at call time, in toolbelt.scope_guard — even if a tool reaches an agent by
     some future mistake, the call is refused and audited.

Two layers because the first one is a property of our wiring, and wiring changes.
"""

from __future__ import annotations

from enum import StrEnum


class Department(StrEnum):
    """A data boundary. Four of them, mirroring how a real care network splits."""

    FAMILY = "family"
    CLINICAL = "clinical"
    BENEFITS = "benefits"
    AUDIT = "audit"


class Scope(StrEnum):
    """Capabilities. Read scopes are cheap; write scopes cross into the world."""

    REGISTRY_READ = "registry:read"
    STATE_READ = "state:read"
    STATE_WRITE = "state:write"

    STORAGE_READ = "storage:read"
    STAGING_WRITE = "staging:write"

    MEDGRAPH_READ = "medgraph:read"
    SCHEDULE_WRITE = "schedule:write"

    BENEFITS_READ = "benefits:read"
    DOC_GENERATE = "doc:generate"

    ESCALATION_WRITE = "escalation:write"


#: Which department owns the data behind each scope. A scope with no owner is
#: infrastructure and crosses no boundary.
SCOPE_OWNER: dict[Scope, Department | None] = {
    Scope.REGISTRY_READ: None,
    Scope.STATE_READ: None,
    Scope.STATE_WRITE: None,
    Scope.STORAGE_READ: Department.FAMILY,
    Scope.STAGING_WRITE: Department.FAMILY,
    Scope.MEDGRAPH_READ: Department.CLINICAL,
    Scope.SCHEDULE_WRITE: Department.CLINICAL,
    Scope.BENEFITS_READ: Department.BENEFITS,
    Scope.DOC_GENERATE: Department.BENEFITS,
    Scope.ESCALATION_WRITE: Department.AUDIT,
}

#: Scopes whose effects are visible outside the system. Everything here goes
#: through the action gate regardless of how confident the agent is.
EXTERNAL_EFFECT: frozenset[Scope] = frozenset({Scope.SCHEDULE_WRITE, Scope.DOC_GENERATE})


class ScopeViolation(Exception):
    """Raised when an agent attempts a capability it does not hold."""

    def __init__(self, agent: str, tool: str, scope: Scope) -> None:
        self.agent = agent
        self.tool = tool
        self.scope = scope
        owner = SCOPE_OWNER.get(scope)
        boundary = f" ({owner} boundary)" if owner else ""
        super().__init__(f"{agent} attempted {tool!r}, which requires {scope.value}{boundary}")
