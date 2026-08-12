"""Durable run state: checkpoints and idempotency.

This is the piece that makes a resumable agent safe. The rule the whole design
turns on:

    write the checkpoint BEFORE the side effect, mark it complete AFTER.

A crash between those two points leaves a `pending` checkpoint holding the
idempotency key. On resume we find that key already claimed and skip the step
instead of performing it twice. That is the trap a naive resumable agent falls
into — it comes back up, replays its plan, and orders the second laptop.

Firestore collections
    runs/{run_id}                        current status + cursor
    runs/{run_id}/checkpoints/{step_id}  one document per attempted step
    idempotency/{key}                    claim record, unique per side effect
    audit/{entry_id}                     append-only, never updated
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from google.cloud import firestore

from vigil.config import get_settings
from vigil.telemetry import current_trace_id, log

_log = log("vigil.state")


def now() -> datetime:
    return datetime.now(UTC)


@lru_cache(maxsize=1)
def db() -> firestore.Client:
    return firestore.Client(project=get_settings().project_id)


def idempotency_key(run_id: str, step_id: str, payload: dict[str, Any]) -> str:
    """Stable across retries and process restarts, which rules out anything
    involving time, randomness or dict ordering."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{run_id}|{step_id}|{canonical}".encode()).hexdigest()
    return digest[:32]


class StepAlreadyDone(Exception):
    """Raised when a step's idempotency key is already claimed. Callers treat
    this as success — the work happened, just not on this attempt."""


@dataclass(slots=True)
class Run:
    run_id: str
    kind: str
    status: str = "running"
    cursor: str | None = None


def start_run(kind: str, subject: str, metadata: dict[str, Any] | None = None) -> Run:
    run_id = uuid.uuid4().hex
    db().collection("runs").document(run_id).set(
        {
            "kind": kind,
            "subject": subject,
            "status": "running",
            "cursor": None,
            "metadata": metadata or {},
            "created_at": now(),
            "updated_at": now(),
            "trace_id": current_trace_id(),
        }
    )
    _log.info("run.started", run_id=run_id, kind=kind)
    return Run(run_id=run_id, kind=kind)


def claim_step(run_id: str, step_id: str, payload: dict[str, Any]) -> str:
    """Claim the right to perform a side effect exactly once.

    The claim is a Firestore create, which fails if the document exists. That
    single atomic operation is what stands between a resumed run and a duplicate
    insurance filing.
    """
    key = idempotency_key(run_id, step_id, payload)
    ref = db().collection("idempotency").document(key)
    try:
        ref.create(
            {
                "run_id": run_id,
                "step_id": step_id,
                "status": "pending",
                "claimed_at": now(),
                "trace_id": current_trace_id(),
            }
        )
    except Exception as exc:  # AlreadyExists — someone got here first
        if "already exists" not in str(exc).lower():
            raise
        existing = ref.get().to_dict() or {}
        _log.warning(
            "step.skipped.duplicate",
            run_id=run_id,
            step_id=step_id,
            key=key,
            previous_status=existing.get("status"),
        )
        raise StepAlreadyDone(key) from exc

    db().collection("runs").document(run_id).collection("checkpoints").document(step_id).set(
        {"status": "pending", "key": key, "payload": payload, "started_at": now()}
    )
    return key


def complete_step(
    run_id: str, step_id: str, key: str, result: dict[str, Any] | None = None
) -> None:
    db().collection("idempotency").document(key).update({"status": "done", "completed_at": now()})
    db().collection("runs").document(run_id).collection("checkpoints").document(step_id).update(
        {"status": "done", "result": result or {}, "completed_at": now()}
    )
    db().collection("runs").document(run_id).update({"cursor": step_id, "updated_at": now()})


def fail_step(run_id: str, step_id: str, key: str, error: str) -> None:
    """Release the claim so a retry can legitimately try again. A failure that
    never touched the outside world must not poison the key forever."""
    db().collection("idempotency").document(key).delete()
    db().collection("runs").document(run_id).collection("checkpoints").document(step_id).update(
        {"status": "failed", "error": error, "failed_at": now()}
    )


def finish_run(run_id: str, status: str = "done") -> None:
    db().collection("runs").document(run_id).update({"status": status, "updated_at": now()})


#: How long an audit write may block the caller. Short on purpose — see audit().
AUDIT_TIMEOUT_S = 5.0

#: The run a call is happening inside, carried ambiently.
#:
#: Tools are called by the model, not by us, so a tool signature contains what
#: the model needs to decide — a source_uri — and not the bookkeeping. That left
#: the most important audit entry in the system untagged: the trust boundary
#: blocks an injected document from inside `read_artifact`, which has no run_id
#: to record, so the block never appeared in that run's trace. The one event the
#: whole design exists to produce was invisible on the screen built to show it.
#:
#: A context variable fixes it without putting plumbing in the model's way, and
#: without a global: each task gets its own value, so concurrent runs cannot
#: attribute each other's entries.
_current_run: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "vigil_current_run", default=None
)


def set_current_run(run_id: str | None) -> contextvars.Token:
    """Bind the run for everything called from here down. Reset with the token."""
    return _current_run.set(run_id)


def reset_current_run(token: contextvars.Token) -> None:
    _current_run.reset(token)


def audit(action: str, actor: str, decision: str, **details: Any) -> str:
    """Append-only. Audit entries are written, never updated or deleted — that is
    the whole point of having them.

    Two things make this more careful than a plain write.

    **It is on the hot path.** The scope guard audits every refused tool call, so
    this function sits inside the agent loop. An unreachable datastore made the
    whole fleet hang: the Firestore client retried for minutes while the agent sat
    silent behind it. A security control that stops the system when its logbook is
    unavailable has turned itself into the outage.

    **Losing the entry silently is also wrong.** So the write is bounded, and on
    failure the entry goes to the structured log — which is Cloud Logging in
    production — tagged so a gap in Firestore can be reconciled against it. The
    failure itself is recorded too. Degrade, do not disappear, and never block.
    """
    entry_id = uuid.uuid4().hex

    # Fill in the run from the ambient context when the caller did not pass one.
    # An explicit run_id always wins — the context is a fallback, not an override.
    if "run_id" not in details and (ambient := _current_run.get()):
        details = {**details, "run_id": ambient}

    record = {
        "action": action,
        "actor": actor,
        "decision": decision,
        "details": details,
        "trace_id": current_trace_id(),
        "at": now(),
    }

    # Log first: whatever happens to the datastore, the entry exists somewhere.
    _log.info("audit", entry_id=entry_id, action=action, actor=actor, decision=decision, **details)

    try:
        # retry=None is load-bearing. `timeout=` alone is ignored here: the
        # client's default Retry carries its own 60-second deadline and that is
        # what governs, so a dead datastore blocked the agent for 55 seconds
        # despite a 5-second timeout. Disabling the retry makes the bound real.
        # Audit entries do not need transport retry anyway — the log fallback
        # below is a better safety net than waiting.
        db().collection("audit").document(entry_id).set(record, retry=None, timeout=AUDIT_TIMEOUT_S)
    except Exception as exc:
        _log.error(
            "audit.persist_failed",
            entry_id=entry_id,
            action=action,
            error=str(exc)[:200],
            note="entry survives in this log; reconcile against Firestore",
        )

    return entry_id
