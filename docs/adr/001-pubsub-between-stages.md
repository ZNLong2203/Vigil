# 001 — Pub/Sub between stages, not direct calls

**Status:** accepted

## Context

Ingestion, orchestration and execution have wildly different runtimes. Accepting
a photo takes milliseconds; extracting structure from it and deciding what to do
next can take a minute, and a care workflow spans weeks. If the ingress called
the agents directly, a slow model call would hold an HTTP connection open and a
crash mid-call would lose the event entirely.

## Decision

Stages communicate over Pub/Sub topics. The API's only job is to persist a run
and publish; everything downstream consumes from the bus.

## Alternatives rejected

- **Direct function calls.** Simplest, and the failure mode is unacceptable: a
  worker crash takes the request with it and the event is gone.
- **A database-backed job table with polling.** Works, but re-implements dead
  lettering, retry backoff and delivery guarantees that Pub/Sub already has.

## Consequences

We accept eventual consistency: a caller gets a `run_id` back, not a result.
The UI is built around watching a run progress rather than awaiting a response.
In exchange, an event survives a worker crash, retries are bounded, and messages
that fail five times land in a dead-letter topic where they become evidence
instead of an infinite loop.
