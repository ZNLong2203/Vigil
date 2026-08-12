# 006 — Eval gate + anti-gaming judge before promoting a self-improvement

**Status:** accepted

## Context

Vigil learns from corrections: when a caregiver rewrites a reminder or rejects a
proposed action, that is signal. The obvious move is to let an agent rewrite its
own instructions from that signal. The obvious failure is Goodhart's law — the
agent optimises the score rather than the job, by answering shorter, declining
hard cases, or quietly redefining what counts as success.

## Decision

A proposed instruction version is promoted only if it clears two independent
gates: a fixed golden eval set it cannot see or modify, and an adversarial judge
on the stronger model whose only task is to argue that the score improved for
the wrong reason. Failing either gate rejects the version and records why.
Promoted versions are versioned entries in the Agent Registry.

## Alternatives rejected

- **Auto-promote on score improvement.** This is the failure mode, not a design.
- **Human review of every proposal.** Correct, and it defeats the point of an
  agent that improves while you are asleep. Humans review the rejections.

## Consequences

Self-improvement is slow and most proposals are rejected, which is the intended
shape. The eval set becomes a load-bearing asset and must be curated by hand.
The rejection log is one of the more interesting artefacts the system produces:
a record of an agent trying to cheat and being caught.
