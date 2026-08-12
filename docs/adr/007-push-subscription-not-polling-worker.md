# 007 — Pub/Sub push to Cloud Run, not a polling worker

**Status:** accepted

## Context

ADR 001 puts a bus between stages, which leaves the question of what consumes
it. A pull subscriber is the natural shape for a background worker, but on Cloud
Run a process that sits in a `subscribe()` loop needs an always-warm instance.
For a system that is idle almost all of the time, that is a bill for waiting.

## Decision

In the cloud, Pub/Sub pushes to a `/pubsub/push` endpoint on the Cloud Run
service, authenticated by OIDC on a dedicated push service account. Locally, a
pull worker consumes the same subscription. Both call the same `handle_event`,
so there is one implementation of the durability guarantees and two thin
adapters.

## Alternatives rejected

- **Pull worker in the cloud with `min-instances=1`.** A fixed hourly cost, and
  the hackathon's own guidance is to keep minimum instances at zero.
- **Cloud Run Jobs triggered by Eventarc.** Better for genuinely long batch work;
  heavier to set up, and the per-event work here fits inside a request.

## Consequences

Each event is bounded by the Cloud Run request timeout (set to 900s), so work
that outgrows that must be split across checkpointed steps — which the design
already requires for resumability. The local and cloud paths differ in how a
message arrives, so the push endpoint needs its own test. In exchange the
service costs nothing between events, and the local demo still gets a worker
process with a visible log stream to kill on camera.
