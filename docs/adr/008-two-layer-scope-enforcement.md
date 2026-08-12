# 008 — Scope enforcement in two layers, not in the prompt

**Status:** accepted

## Context

Each agent belongs to a department with a different data boundary: the benefits
agent must never read a clinical note, the watchdog must never change anything.
The cheap way to express that is a sentence in the system prompt. The problem is
that a sentence is a request, and a model working hard on a plausible-looking
task will occasionally talk itself past one.

## Decision

Scopes are capabilities held by a registry entry, enforced twice.

1. **At assembly.** `toolbelt.build_belt` gives an agent only the tools whose
   scope its entry holds, so the model never receives a declaration for anything
   else.
2. **At call time.** A `before_tool_callback` re-checks on every invocation.
   Returning a dict from that callback short-circuits the tool: it never runs,
   the model gets a refusal it can reason about, and an audit entry is written.

A tool with no scope tag is excluded rather than allowed.

## Alternatives rejected

- **Instruction only.** Unenforceable, and untestable — there is no assertion you
  can write about a sentence.
- **Assembly only.** Correct today. Layer 1 is a property of our wiring, and
  wiring is what changes when someone adds an agent in week three.
- **Raising an exception at call time.** An exception inside the model's loop is
  much harder for it to recover from than a result explaining the refusal.

## Consequences

Two places to keep in step, covered by `tests/test_fleet_scopes.py`. The refusal
text is written for the model rather than for a log reader: it states that a
retry will not succeed and names the legitimate route, because a refusal read as
transient produces a retry loop, which turns a security control into a cost
incident.
