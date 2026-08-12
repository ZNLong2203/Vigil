"""The trust boundary: everything untrusted crosses here, once.

Two controls, applied in this order:

  redact()   replace identifiers with stable tokens, so the reasoning tier never
             holds a policy number or an email address it does not need
  screen()   detect instructions hidden inside content, so a document cannot
             give the fleet orders

Order matters. Screening runs on redacted text, which means an injection payload
that embeds an exfiltration address has already lost the address by the time we
decide what to do with it.

**What this is.** A local fallback, deliberately conservative and deliberately
dumb. In a deployed project Model Armor is the control and this is the thing that
keeps the system honest when there is no cloud project attached — which is most
of the time during development, and all of the time in CI.

**What this is not.** A complete defence. Pattern matching cannot catch a
paraphrase, and identifier redaction by regex cannot catch a name. Both gaps are
why the deployed path uses a model: Model Armor for screening, Gemma for
redaction. The architecture is the layering, not the patterns.

The one property it does hold, and the reason it is worth having at all: content
that fails screening never becomes part of a prompt. A finding here is terminal
for that content, not advisory.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from vigil.telemetry import log

_log = log("vigil.guardrails")


class FindingKind(StrEnum):
    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_HIJACK = "role_hijack"
    EXFILTRATION = "exfiltration"
    FALSE_COMPLETION = "false_completion"


@dataclass(slots=True)
class Finding:
    kind: FindingKind
    excerpt: str
    pattern: str


@dataclass(slots=True)
class ScreenResult:
    safe: bool
    text: str
    findings: list[Finding] = field(default_factory=list)
    redactions: int = 0

    @property
    def summary(self) -> str:
        if self.safe:
            return f"clean · {self.redactions} identifiers tokenised"
        kinds = ", ".join(sorted({str(f.kind) for f in self.findings}))
        return f"blocked · {kinds}"


# ── Injection signatures ─────────────────────────────────────────────────────
#
# Phrased as an attacker would, not as a defender would like. Each pattern below
# corresponds to something that actually appears in real payloads: cancelling
# prior context, claiming elevated authority, redirecting data outward, and
# declaring the task finished so nobody looks further.

_INJECTION_PATTERNS: list[tuple[FindingKind, str]] = [
    (
        FindingKind.INSTRUCTION_OVERRIDE,
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
    ),
    (FindingKind.INSTRUCTION_OVERRIDE, r"disregard\s+(?:all\s+)?(?:previous|prior|earlier)\b"),
    (FindingKind.INSTRUCTION_OVERRIDE, r"system\s+override"),
    (FindingKind.INSTRUCTION_OVERRIDE, r"new\s+instructions?\s*:"),
    (
        FindingKind.ROLE_HIJACK,
        r"you\s+are\s+now\s+(?:in\s+)?(?:an?\s+)?(?:admin|administrator|developer|root)",
    ),
    (FindingKind.ROLE_HIJACK, r"(?:enter|activate)\s+(?:admin|developer|debug)\s+mode"),
    (FindingKind.ROLE_HIJACK, r"as\s+an?\s+(?:admin|system)\s+you\s+(?:must|should|can)"),
    (
        FindingKind.EXFILTRATION,
        r"(?:export|send|forward|email|upload)\s+(?:the\s+)?(?:complete\s+|full\s+|all\s+)?(?:patient\s+)?records?\b",
    ),
    (FindingKind.EXFILTRATION, r"(?:send|forward|email)\s+(?:this|it|them)\s+to\s+\S+@"),
    (FindingKind.FALSE_COMPLETION, r"(?:reply|respond)\s+only\s+with"),
    (
        FindingKind.FALSE_COMPLETION,
        r"mark\s+(?:this|the)\s+(?:task|workflow|run)\s+(?:as\s+)?(?:complete|done)",
    ),
]

_COMPILED = [(kind, re.compile(p, re.IGNORECASE)) for kind, p in _INJECTION_PATTERNS]


# ── Identifier signatures ────────────────────────────────────────────────────
#
# Structured identifiers only. A person's name needs a model, which is exactly
# what the Gemma tier is for — see docs/adr/005.

_REDACTION_PATTERNS: list[tuple[str, str]] = [
    # Each dot must be followed by more label, so a sentence-ending period is
    # not swallowed into the address — an over-capturing pattern would put the
    # wrong value in the token map, and the token map is what de-tokenises.
    ("EMAIL", r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("PHONE", r"(?<!\d)(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){9,13}\d(?!\d)"),
    # Consume every hyphenated segment, not a fixed three. The original stopped
    # after three and left the fourth behind: "NM-SYNTH-4471-B" redacted to
    # "[POLICY_1]-B", which looks redacted and is not. Requiring at least two
    # segments keeps ordinary hyphenated text like "CC-12" out.
    ("POLICY", r"\b[A-Z]{2,4}(?:-[A-Z0-9]{1,8}){2,}\b"),
    ("ACCESSION", r"\b(?:SYNTH|ACC|REF)-[A-Z0-9-]{4,}\b"),
]

_REDACTION_COMPILED = [(label, re.compile(p)) for label, p in _REDACTION_PATTERNS]


def redact(text: str) -> tuple[str, int, dict[str, str]]:
    """Replace identifiers with stable tokens.

    Returns the redacted text, how many substitutions were made, and the token
    map. **The map is as sensitive as the original** — it belongs in the action
    layer, at the moment a side effect genuinely needs a real value, and nowhere
    near a prompt.

    Tokens are stable within one document, so `[EMAIL_1]` refers to the same
    address everywhere it appears and the model can still reason about identity
    without holding the value.
    """
    # Collect every match first, then resolve overlaps, then replace once.
    #
    # Replacing pattern-by-pattern looked fine and was not. "NM-SYNTH-4471-B"
    # matches POLICY as "NM-SYNTH-4471" and ACCESSION as "SYNTH-4471-B"; applying
    # both left "[POLICY_1]-B" — a partial redaction that leaks the suffix while
    # looking redacted, and a token map with an entry that no longer appears in
    # the text, so de-tokenisation would fail on it too.
    #
    # Longest match wins, ties broken by position. An identifier is one thing.
    spans: list[tuple[int, int, str, str]] = []
    for label, pattern in _REDACTION_COMPILED:
        for match in pattern.finditer(text):
            spans.append((match.start(), match.end(), label, match.group(0)))

    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))

    chosen: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, label, value in spans:
        if start >= last_end:
            chosen.append((start, end, label, value))
            last_end = end

    token_map: dict[str, str] = {}
    counters: dict[str, int] = {}
    value_to_token: dict[str, str] = {}
    pieces: list[str] = []
    cursor = 0

    for start, end, label, value in chosen:
        if value not in value_to_token:
            counters[label] = counters.get(label, 0) + 1
            token = f"[{label}_{counters[label]}]"
            value_to_token[value] = token
            token_map[token] = value
        pieces.append(text[cursor:start])
        pieces.append(value_to_token[value])
        cursor = end

    pieces.append(text[cursor:])
    result = "".join(pieces)

    # A repeated identifier further along the text is the same identifier: the
    # span pass only catches the occurrences the patterns found, so sweep the
    # rest by value to keep tokens stable across the whole document.
    for value, token in value_to_token.items():
        result = result.replace(value, token)

    return result, len(token_map), token_map


def screen(text: str, *, source_uri: str | None = None) -> ScreenResult:
    """Redact, then look for instructions hiding in content.

    A finding is terminal: the caller must not pass the text to a model. Callers
    get the redacted text back either way so the *finding itself* can be shown to
    a human without leaking identifiers.

    Redaction goes through the Gemma tier when one is configured — regex finds
    structured identifiers and cannot find a person's name, which is the one that
    matters most in a care record. Imported here rather than at module scope
    because redaction builds on this module's regex pass.
    """
    from vigil.redaction import redact as tiered_redact

    result = tiered_redact(text)
    redacted, redaction_count = result.text, result.count
    if not result.used_model:
        _log.warning(
            "guardrail.regex_only",
            source_uri=source_uri,
            note=result.note,
            detail="names and addresses are NOT redacted on this path",
        )

    findings = [
        Finding(kind=kind, excerpt=_excerpt(redacted, match), pattern=pattern.pattern)
        for kind, pattern in _COMPILED
        if (match := pattern.search(redacted))
    ]

    result = ScreenResult(
        safe=not findings, text=redacted, findings=findings, redactions=redaction_count
    )

    if findings:
        _log.warning(
            "guardrail.blocked",
            source_uri=source_uri,
            kinds=sorted({str(f.kind) for f in findings}),
            count=len(findings),
        )
    else:
        _log.info("guardrail.clean", source_uri=source_uri, redactions=redaction_count)

    return result


def _excerpt(text: str, match: re.Match[str], window: int = 90) -> str:
    start = max(0, match.start() - window // 3)
    end = min(len(text), match.end() + window)
    return " ".join(text[start:end].split())
