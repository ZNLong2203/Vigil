# 010 — Hard policy rules run before confidence rules

**Status:** accepted

## Context

The action gate decides whether an action can happen unattended. The obvious
design is a score: combine risk and the agent's confidence, compare to a
threshold, act if it clears. It reads as principled and it is wrong in one
specific place.

An agent that is *certain* about a medication change is the agent you least want
acting alone. Certainty is what a confident hallucination feels like from the
inside, and a scoring system rewards it: the more sure the model is, the fewer
checks it faces.

## Decision

Rules are ordered and the first match wins. Hard rules — properties of the action
itself — come first:

    1. deny.unscoped          the agent does not hold this capability
    2. approve.clinical       clinical data, always, at any confidence
    3. approve.external       irreversible outside this system

Then the soft rules, which are properties of how the agent feels:

    4. approve.high_risk
    5. approve.low_confidence
    6. allow.default

Confidence can only ever make the gate *stricter*. Every decision carries the id
of the rule that produced it.

## Alternatives rejected

- **Weighted score.** Lets a confident agent buy its way past a clinical gate.
- **Approve everything.** Safe, and it makes the fleet pointless; a system that
  interrupts you for every reversible staging write is one you turn off.
- **A boolean verdict.** "Denied" is not auditable. "Denied by `deny.unscoped`"
  is something an auditor can argue with and an engineer can grep for.

## Consequences

The gate is noisier than a tuned scorer would be: every clinical change and every
outbound document waits for a human, even the obvious ones. That is the intended
cost. `deny.unscoped` also duplicates a check the toolbelt already makes (ADR
008) — deliberately, because a request arriving here for a capability the agent
does not hold means something upstream is broken, and the safe reading of a
broken upstream is that the request cannot be trusted.

Locked in by `test_confidence_cannot_buy_past_a_clinical_gate`.
