"""Structured output contracts.

Every agent returns a validated object, never prose. Two reasons, and the second
matters more:

  1. Prose has to be parsed, and a parser is a place where a hallucination turns
     into a plausible value.
  2. A schema is where confidence and provenance become mandatory. An agent
     cannot report a dosage without also saying how sure it is and which document
     it read it from, because the field is required.

Provenance is the load-bearing idea: the conflict-resolution behaviour in the
demo — week 1 says 5 mg, week 3 says 10 mg, and the system refuses to silently
pick the newer one — only works because every claim carries its source.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Confidence(BaseModel):
    """Never a bare float. A number with no reason attached cannot be argued with."""

    value: float = Field(ge=0.0, le=1.0, description="0 = guess, 1 = certain")
    reason: str = Field(description="What made it this high or this low, in one sentence")


class Provenance(BaseModel):
    source_uri: str = Field(description="gs:// path or document id the claim came from")
    excerpt: str | None = Field(
        default=None, description="The span of source text supporting the claim"
    )
    observed_at: str | None = Field(default=None, description="ISO timestamp on the source")


class Claim(BaseModel):
    """One extracted fact. The unit that memory stores and the watchdog verifies."""

    field: str
    value: str
    confidence: Confidence
    provenance: Provenance


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StructuredEvent(BaseModel):
    """intake-agent output."""

    kind: str = Field(description="document | photo | voice_note | webhook")
    summary: str = Field(description="One line a tired human can read at a glance")
    claims: list[Claim]
    language: str | None = Field(default=None, description="e.g. 'en', 'vi', 'vi+en'")
    needs_human: bool = Field(
        default=False, description="True when the artifact was too degraded to trust"
    )


class Delegation(BaseModel):
    """One hop in the orchestrator's plan."""

    agent: str = Field(description="Registry name of the agent to call")
    reason: str = Field(description="Why this agent and not another")
    input_summary: str


class RunPlan(BaseModel):
    """orchestrator output. The plan is data, so it can be checkpointed, replayed
    and audited — a plan that only exists inside a prompt cannot be any of those."""

    intent: str = Field(description="What this run is trying to achieve")
    delegations: list[Delegation]
    stop_reason: str | None = Field(
        default=None, description="Set when the orchestrator decides to do nothing"
    )


class ScheduleChange(BaseModel):
    medication: str
    from_time: str | None = None
    to_time: str
    reason: str


class ScheduleProposal(BaseModel):
    """meds-agent output. A proposal, never an applied change — clinical writes
    go through the action gate without exception."""

    changes: list[ScheduleChange]
    collisions_found: list[str] = Field(default_factory=list)
    interactions_found: list[str] = Field(default_factory=list)
    confidence: Confidence
    risk: Risk


class Contradiction(BaseModel):
    """Two sources that disagree. Deliberately has no `winner` field: recency is
    not evidence, and the system is not entitled to break the tie."""

    field: str
    values: list[Claim] = Field(min_length=2)
    note: str = Field(description="What a human needs to know to settle it")


class Verdict(BaseModel):
    """watchdog output."""

    verified: bool
    unsupported_claims: list[str] = Field(
        default_factory=list, description="Claims with no backing in persisted state"
    )
    contradictions: list[Contradiction] = Field(default_factory=list)
    escalate: bool = Field(default=False)
    reasoning: str
