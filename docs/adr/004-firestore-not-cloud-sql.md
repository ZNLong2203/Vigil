# 004 — Firestore, not Cloud SQL

**Status:** accepted

## Context

The system stores four very different things: run state, per-step checkpoints,
idempotency claims, and an append-only audit log. Intake events arrive with no
stable shape — a scanned lab result and a voice note extract into different
fields, and the schema will change several times during a three-week build.

## Decision

Firestore in native mode, with one collection per concern and subcollections for
per-run checkpoints.

## Alternatives rejected

- **Cloud SQL.** Better for relational queries and constraints, but it does not
  scale to zero. An always-on instance is a fixed daily cost for a system that is
  idle almost all the time, and migrations during a short build are pure drag.
- **Cloud Storage + JSON files.** No atomic create, which kills ADR 002 —
  claiming an idempotency key needs a genuine compare-and-set.

## Consequences

We give up joins and foreign keys, so cross-collection integrity is our
responsibility. Two things buy that back: Firestore's atomic document create is
exactly the primitive the idempotency claim needs, and the free tier plus
scale-to-zero keeps the running cost near nothing. Firestore's vector search
also covers episodic memory without a separate always-on vector database — at
the cost that the local emulator does not support vector search, so local runs
fall back to an in-memory index.
