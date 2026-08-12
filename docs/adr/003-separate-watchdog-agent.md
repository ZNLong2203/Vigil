# 003 — A separate read-only watchdog, not self-critique

**Status:** accepted

## Context

Worker agents will occasionally assert things that are not in the record — a
dosage that appears nowhere in the source documents, a deadline it inferred
rather than read. Any of those reaching the action gate is a real-world error.

## Decision

A distinct `watchdog` agent, with read-only tool scope, verifies worker output
against the persisted state before the action gate will accept it. It also
counts steps, detects repeated states, and escalates to a human with its
reasoning attached when confidence is low.

## Alternatives rejected

- **Self-critique in the same prompt** ("now check your work"). A model
  reviewing its own output shares the context and the failure mode that produced
  the error; it tends to confirm rather than catch. Correlated reviewers are
  barely better than no reviewer.
- **Schema validation alone.** Catches malformed output, not confident nonsense
  that happens to fit the schema.

## Consequences

An extra model call per step, and a second place where a bug can block valid
work. We accept both: the watchdog runs on the cheap model by default, and every
block it issues is written to the audit log with the evidence it used, so a
false positive is diagnosable rather than mysterious.
