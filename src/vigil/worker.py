"""Background execution: take an event off the bus and put it through the fleet.

Two adapters, one implementation. `handle_event` is the whole of it; the pull
loop below is for local development, where a terminal you can kill mid-flight is
worth more than a webhook, and the `/pubsub/push` endpoint in api.py is what runs
in the cloud (see ADR 007). Both await the same coroutine, so the durability
guarantees cannot drift between them.

Kill this process mid-run and start it again: the redelivered message finds each
completed hop already claimed and skips it, so a crash costs the step in flight
and nothing else. `make chaos` does exactly that on purpose.
"""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any

from google.cloud import pubsub_v1

from vigil.bus import ensure_subscription, subscriber, subscription_path
from vigil.config import get_settings
from vigil.fleet.budget import RunBudget
from vigil.fleet.pipeline import orchestrate
from vigil.state import audit, finish_run
from vigil.telemetry import log, setup_telemetry, span

setup_telemetry("vigil-worker")
_log = log("vigil.worker")


async def handle_event(payload: dict[str, Any]) -> None:
    """Put one event through the fleet.

    Terminal states are recorded on the run rather than raised. A run that was
    escalated, budget-capped or simply had nothing to do is a finished run with
    an outcome — not an error — and the caller needs to ack the message either
    way. Only an unexpected exception nacks, because only that is worth retrying.
    """
    run_id = payload["run_id"]
    budget = RunBudget(run_id=run_id)

    with span("worker.handle", run_id=run_id, kind=payload.get("kind")):
        settings = get_settings()
        if not settings.model_enabled:
            # The skeleton path: no credentials, so there is no fleet to run.
            # Say so on the run rather than pretending the work happened.
            _log.info("model.skipped", run_id=run_id, reason="no credentials configured")
            audit("run.skipped", actor="worker", decision="skipped", run_id=run_id)
            finish_run(run_id, "skipped")
            return

        try:
            result = await orchestrate(payload, budget)
        except Exception as exc:
            audit("run.failed", actor="worker", decision="failed", run_id=run_id, error=str(exc))
            finish_run(run_id, "failed")
            raise

        if result.stopped_by == "plan_step_replayed":
            # Another delivery of this same message is still working. Pub/Sub
            # redelivers when a run outlasts the ack deadline, and a fleet run is
            # minutes long, so this is routine rather than exceptional.
            #
            # Acking is right — the work is in hand. Writing a status is not: the
            # run is still in progress, and stamping it "stopped" from here would
            # mark a live run finished and mislead every reader of it. The
            # delivery that owns the run is the only one that may close it.
            _log.info("worker.replay_ignored", run_id=run_id)
            return

        status = (
            "awaiting_human" if result.escalated else "stopped" if result.stopped_by else "done"
        )
        finish_run(run_id, status)
        audit(
            "run.finished",
            actor="worker",
            decision=status,
            run_id=run_id,
            agents=len(result.agent_runs),
            tokens=result.total_tokens,
            denials=len(result.denials),
        )
        _log.info("worker.done", run_id=run_id, status=status, summary=result.summary())


# ── Local pull adapter ───────────────────────────────────────────────────────


def _callback(message: pubsub_v1.subscriber.message.Message) -> None:
    try:
        payload = json.loads(message.data.decode())
    except json.JSONDecodeError:
        _log.error("message.undecodable", message_id=message.message_id)
        message.ack()  # never redeliver garbage; the DLQ is for real failures
        return

    try:
        asyncio.run(handle_event(payload))
        message.ack()
    except Exception as exc:
        _log.error("message.failed", message_id=message.message_id, error=str(exc))
        message.nack()  # five nacks and the dead-letter policy takes over


def main() -> None:
    s = get_settings()
    ensure_subscription(s.subscription_worker, s.topic_events, dlq_topic=s.topic_dlq)
    path = subscription_path(s.subscription_worker)

    client = subscriber()
    future = client.subscribe(
        path,
        callback=_callback,
        # One at a time. An agent hop costs 10-30 seconds and the budget is
        # per-run, so pulling a batch would just queue work behind a wall of
        # model latency without finishing anything sooner.
        flow_control=pubsub_v1.types.FlowControl(max_messages=1),
    )
    _log.info("worker.listening", subscription=s.subscription_worker, project=s.project_id)

    def _stop(signum, _frame):
        _log.info("worker.stopping", signal=signum)
        future.cancel()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    with client:
        try:
            future.result()
        except (KeyboardInterrupt, FuturesTimeout):
            future.cancel()
            future.result()


if __name__ == "__main__":
    sys.exit(main())
