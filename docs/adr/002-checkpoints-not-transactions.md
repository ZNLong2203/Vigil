# 002 — Checkpoints + idempotency keys, not transactions

**Status:** accepted

## Context

A resumable agent has a specific way of going wrong: it comes back up after a
crash, replays its plan, and performs a side effect that already happened. In
this domain that means a benefits claim filed twice or an appointment booked
twice — both of which cost a caregiver real time to unwind.

## Decision

Every side effect is guarded by an idempotency key derived from
`sha256(run_id, step_id, canonical_payload)`. The key is claimed by an atomic
Firestore document create *before* the side effect and marked complete *after*.
A resumed run that finds the key already claimed skips the step.

## Alternatives rejected

- **Database transactions.** They cannot span an external side effect. Booking
  an appointment through a third-party API is not rollback-able, so a
  transaction would give false confidence.
- **A "did I already do this?" query against the target system.** Depends on
  every integration exposing a reliable way to ask, which none of them do
  uniformly.

## Consequences

The key must be perfectly deterministic, which rules out timestamps, random
values and unordered dict serialisation — enforced by
[`tests/test_idempotency.py`](../../tests/test_idempotency.py). A step that
fails *before* touching the outside world explicitly releases its claim, so a
transient error does not permanently wedge the run.
