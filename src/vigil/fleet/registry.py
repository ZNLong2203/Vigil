"""Agent Registry — publish, version and discover.

This is what makes the fleet an institution rather than a script. An orchestrator
does not import a worker; it looks one up by capability, reads what the worker is
allowed to touch, and calls it only if the registry says it may.

Entries are the source of truth for tool scopes. toolbelt.build_belt reads them,
which means changing what an agent can do is a registry edit and an audit trail,
not a code change nobody notices in review.

Firestore collection: `registry/{name}` with a `versions` subcollection.
The shape matches web/lib/registry.ts so the UI renders real entries unchanged.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from vigil.fleet.scopes import Department, Scope
from vigil.state import db, now
from vigil.telemetry import log

_log = log("vigil.registry")

COLLECTION = "registry"


@dataclass(slots=True)
class EvalResult:
    suite: str
    score: float
    cases: int
    anti_gaming_passed: bool


@dataclass(slots=True)
class VersionRecord:
    version: str
    status: str  # promoted | rejected | superseded
    eval_score: float
    anti_gaming_passed: bool
    at: str
    #: Present on rejections. An improvement refused without a stated reason is
    #: indistinguishable from a bug.
    reason: str | None = None


@dataclass(slots=True)
class AgentEntry:
    name: str
    version: str
    owner: Department
    summary: str
    capability_input: str
    capability_output: str
    tool_scopes: list[Scope]
    callable_by: list[str]
    eval: EvalResult
    model: str = "fast"  # "fast" | "deep" — resolved against settings at build time
    history: list[VersionRecord] = field(default_factory=list)

    @property
    def runtime_name(self) -> str:
        """ADK requires node names to be valid Python identifiers.

        The registry keeps the published name — that is what appears in the
        catalogue, in audit entries and in the UI — and the runtime gets a
        mangled copy. Bending the catalogue to a framework constraint would be
        the wrong way round.
        """
        return self.name.replace("-", "_")

    def holds(self, scope: Scope) -> bool:
        return scope in self.tool_scopes

    def may_be_called_by(self, caller: str) -> bool:
        """An empty callable_by means an entry point — reachable from the bus,
        not from another agent."""
        return caller in self.callable_by

    def to_document(self) -> dict[str, Any]:
        doc = asdict(self)
        doc["owner"] = str(self.owner)
        doc["tool_scopes"] = [str(s) for s in self.tool_scopes]
        doc["updated_at"] = now()
        return doc


# ─────────────────────────────────────────────────────────────────────────────
# The fleet as published. Five agents, four boundaries.
#
# Read the tool_scopes column as the answer to "what could this agent do on its
# worst day". intake-agent can write to staging and nowhere else; watchdog can
# read everything and change nothing; orchestrator holds no business scope at
# all — it can only look agents up and call them.
# ─────────────────────────────────────────────────────────────────────────────

FLEET: list[AgentEntry] = [
    AgentEntry(
        name="orchestrator",
        version="2.1.0",
        owner=Department.FAMILY,
        summary=(
            "Routes work, owns budgets and checkpoints, assigns idempotency keys. "
            "Holds no business tools of its own."
        ),
        capability_input="CleanEvent",
        capability_output="RunPlan",
        tool_scopes=[Scope.REGISTRY_READ, Scope.STATE_WRITE],
        callable_by=[],
        eval=EvalResult("routing-v4", 0.93, 30, True),
        model="fast",
    ),
    AgentEntry(
        name="intake-agent",
        version="1.7.1",
        owner=Department.FAMILY,
        summary=(
            "Turns photos, voice notes and scans into structured events. Writes to "
            "staging only — it can never cause an external side effect."
        ),
        capability_input="RawArtifact",
        capability_output="StructuredEvent",
        tool_scopes=[Scope.STORAGE_READ, Scope.STAGING_WRITE],
        callable_by=["orchestrator"],
        eval=EvalResult("extraction-v6", 0.89, 24, True),
        model="fast",
    ),
    AgentEntry(
        name="meds-agent",
        version="1.4.2",
        owner=Department.CLINICAL,
        summary=(
            "Medication schedule, collision and interaction detection. Reads the "
            "medication graph; proposes a schedule but never writes a clinical record."
        ),
        capability_input="MedicationContext",
        capability_output="ScheduleProposal",
        tool_scopes=[Scope.MEDGRAPH_READ, Scope.SCHEDULE_WRITE],
        callable_by=["orchestrator", "watchdog"],
        eval=EvalResult("meds-v3", 0.91, 20, True),
        model="fast",
    ),
    AgentEntry(
        name="benefits-agent",
        version="1.2.0",
        owner=Department.BENEFITS,
        summary=(
            "Tracks insurance deadlines and drafts forms. Generates documents; "
            "submitting one is always gated on a human."
        ),
        capability_input="BenefitsContext",
        capability_output="DraftDocument",
        tool_scopes=[Scope.BENEFITS_READ, Scope.DOC_GENERATE],
        callable_by=["orchestrator"],
        eval=EvalResult("benefits-v2", 0.87, 18, True),
        model="fast",
    ),
    AgentEntry(
        name="watchdog",
        version="1.1.3",
        owner=Department.AUDIT,
        summary=(
            "Read-only verifier. Checks other agents against persisted state, "
            "detects repeated states, escalates on low confidence. Cannot act."
        ),
        capability_input="AgentOutput",
        capability_output="Verdict",
        tool_scopes=[Scope.STATE_READ, Scope.ESCALATION_WRITE],
        callable_by=["orchestrator"],
        eval=EvalResult("verify-v5", 0.95, 26, True),
        # The verifier runs on the stronger model. A weak reviewer of a strong
        # worker is theatre.
        model="deep",
    ),
]

_BY_NAME: dict[str, AgentEntry] = {entry.name: entry for entry in FLEET}


def lookup(name: str) -> AgentEntry:
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"no agent named {name!r} in the registry") from exc


def discover(capability_input: str, caller: str) -> list[AgentEntry]:
    """Find agents that accept this input *and* that the caller is allowed to
    call. Discovery that ignores permission is just a directory."""
    return [
        entry
        for entry in FLEET
        if entry.capability_input == capability_input and entry.may_be_called_by(caller)
    ]


def publish(entry: AgentEntry) -> None:
    """Write an entry to Firestore. Idempotent — publishing an unchanged entry is
    a no-op from the reader's point of view."""
    db().collection(COLLECTION).document(entry.name).set(entry.to_document())
    for record in entry.history:
        db().collection(COLLECTION).document(entry.name).collection("versions").document(
            record.version
        ).set(asdict(record))
    _log.info("registry.published", agent=entry.name, version=entry.version)


def publish_fleet() -> int:
    for entry in FLEET:
        publish(entry)
    return len(FLEET)
