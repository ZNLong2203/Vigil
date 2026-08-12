"""Claims, provenance, and disagreement.

A claim is the unit of memory: one field, one value, where it came from, and how
sure the agent was. Storing values without their source would make the rest of
this module impossible — you cannot describe a disagreement if you cannot say who
said what.

The load-bearing decision here is a missing feature. `detect_contradictions`
returns disagreements and stops. There is no `resolve()`, no "newest wins", no
confidence tie-break. Over three weeks of care notes, a later document is
routinely a transcription error, and a system that silently prefers it will
quietly change a dose. The correct behaviour is to notice, refuse, and escalate
with both sources attached — which is what the watchdog does with what this
returns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from vigil.state import db, now
from vigil.telemetry import log

_log = log("vigil.memory")


@dataclass(slots=True, frozen=True)
class Claim:
    field: str
    value: str
    confidence: float
    source_uri: str
    observed_at: str
    excerpt: str | None = None
    run_id: str | None = None

    def to_document(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "confidence": self.confidence,
            "source_uri": self.source_uri,
            "observed_at": self.observed_at,
            "excerpt": self.excerpt,
            "run_id": self.run_id,
            "at": now(),
        }


@dataclass(slots=True)
class Contradiction:
    """Two or more sources that disagree on one field.

    Deliberately has no `winner`. See the module docstring.
    """

    field: str
    claims: list[Claim] = field(default_factory=list)

    @property
    def values(self) -> list[str]:
        return [c.value for c in self.claims]

    def describe(self) -> str:
        parts = [
            f"{c.value!r} from {c.source_uri.rsplit('/', 1)[-1]} ({c.observed_at[:10]})"
            for c in sorted(self.claims, key=lambda c: c.observed_at)
        ]
        return (
            f"{self.field}: {' vs '.join(parts)}. "
            f"Nothing in the record explains the change, so this needs a human."
        )


# ── Normalisation ────────────────────────────────────────────────────────────
#
# The point of normalising is to avoid crying wolf. "5 mg", "5mg" and "5 MG" are
# the same claim written by three different scanners; treating them as a conflict
# would bury the one real disagreement under noise. Normalisation stops at
# formatting — it never touches magnitude or unit, because "5 mg" and "5 ml" are
# genuinely different and collapsing them would hide exactly the class of error
# this module exists to surface.

_WHITESPACE = re.compile(r"\s+")
_NUMBER_UNIT = re.compile(r"^(\d+(?:\.\d+)?)\s*([a-z/%]+)$")


def normalise(value: str) -> str:
    text = _WHITESPACE.sub(" ", value.strip().lower())
    if match := _NUMBER_UNIT.match(text):
        number, unit = match.groups()
        number = number.rstrip("0").rstrip(".") if "." in number else number
        return f"{number} {unit}"
    return text


def detect_contradictions(claims: list[Claim]) -> list[Contradiction]:
    """Group claims by field and report the fields where sources disagree.

    Two claims from the *same* source are not a contradiction — that is one
    document being read twice, and the extraction pipeline's problem, not the
    caregiver's.
    """
    by_field: dict[str, list[Claim]] = {}
    for claim in claims:
        by_field.setdefault(claim.field, []).append(claim)

    found: list[Contradiction] = []
    for field_name, group in by_field.items():
        distinct = {normalise(c.value) for c in group}
        if len(distinct) < 2:
            continue
        if len({c.source_uri for c in group}) < 2:
            continue

        # One claim per distinct value, the most confident of each, so the
        # escalation shows the strongest version of both sides.
        best: dict[str, Claim] = {}
        for claim in group:
            key = normalise(claim.value)
            if key not in best or claim.confidence > best[key].confidence:
                best[key] = claim

        found.append(Contradiction(field=field_name, claims=list(best.values())))

    if found:
        _log.warning("memory.contradictions", fields=[c.field for c in found], count=len(found))
    return found


# ── Persistence ──────────────────────────────────────────────────────────────


def remember(subject: str, claim: Claim) -> str:
    ref = db().collection("memory").document(subject).collection("claims").document()
    ref.set(claim.to_document())
    return ref.id


def recall(subject: str, field_name: str | None = None) -> list[Claim]:
    """Read claims back. Nothing is ever superseded in place — a claim that turned
    out to be wrong is still what the record said at the time, and an audit that
    cannot reconstruct the past is not an audit."""
    query = db().collection("memory").document(subject).collection("claims")
    if field_name:
        query = query.where("field", "==", field_name)

    return [
        Claim(
            field=d["field"],
            value=d["value"],
            confidence=d["confidence"],
            source_uri=d["source_uri"],
            observed_at=d["observed_at"],
            excerpt=d.get("excerpt"),
            run_id=d.get("run_id"),
        )
        for doc in query.stream()
        if (d := doc.to_dict())
    ]
