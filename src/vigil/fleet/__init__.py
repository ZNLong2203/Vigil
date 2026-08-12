"""The agent fleet: registry, scopes, budgets, tools and the agents themselves."""

from vigil.fleet.budget import BudgetExceeded, RunBudget
from vigil.fleet.registry import FLEET, AgentEntry, discover, lookup
from vigil.fleet.scopes import Department, Scope, ScopeViolation
from vigil.fleet.toolbelt import build_belt, scope_guard

__all__ = [
    "FLEET",
    "AgentEntry",
    "BudgetExceeded",
    "Department",
    "RunBudget",
    "Scope",
    "ScopeViolation",
    "build_belt",
    "discover",
    "lookup",
    "scope_guard",
]
