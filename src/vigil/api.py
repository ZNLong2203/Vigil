"""Ingress. Accepts an event, publishes it, returns immediately.

The API never does agent work. It is the thin, always-fast tier; everything
expensive happens in the worker, off the request path. That separation is what
lets Cloud Run scale this to zero without stranding half-finished runs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from vigil.bus import ensure_subscription, publish
from vigil.config import get_settings
from vigil.state import audit, db, start_run
from vigil.telemetry import current_trace_id, log, setup_telemetry, span

setup_telemetry("vigil-api")
_log = log("vigil.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Provision the bus on boot. Idempotent, so a cold Cloud Run instance can
    start in a project where the topics do not exist yet without a separate
    provisioning step — and a failure here degrades rather than crashes."""
    s = get_settings()
    try:
        ensure_subscription(s.subscription_worker, s.topic_events, dlq_topic=s.topic_dlq)
    except Exception as exc:
        _log.warning("infrastructure.ensure_failed", error=str(exc))
    yield


app = FastAPI(
    title="Vigil",
    description="An agent fleet that keeps watch, so caregivers don't have to.",
    version="0.1.0",
    lifespan=lifespan,
)
FastAPIInstrumentor.instrument_app(app)


class EventIn(BaseModel):
    kind: Literal["document", "voice_note", "photo", "webhook", "manual"]
    subject: str = Field(description="Care recipient id — pseudonymous, never a real name")
    source_uri: str | None = Field(default=None, description="gs:// path of the raw artifact")
    body: dict[str, Any] = Field(default_factory=dict)


class EventOut(BaseModel):
    run_id: str
    message_id: str
    trace_id: str | None


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Cheap auth on a public Cloud Run URL. Not a security model on its own —
    it exists so stray internet traffic cannot burn the hackathon credits."""
    if x_api_key != get_settings().api_auth_key:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")


# Served at /health, not /healthz.
#
# On Cloud Run, /healthz never reaches the container: Google's frontend answers
# it with its own HTML 404, and nothing appears in the container log — which
# makes it look like the app failed to start when it is serving fine. /docs,
# /openapi.json and / all arrive normally. /healthz is kept as an alias for
# anyone running locally who expects the conventional name.
@app.get("/health")
@app.get("/healthz", include_in_schema=False)
def health() -> dict[str, Any]:
    s = get_settings()
    return {
        "status": "ok",
        "env": s.env,
        "project": s.project_id,
        "vertex_location": s.vertex_location,
        "emulators": s.uses_emulators,
        "model_enabled": s.model_enabled,
        "model_fast": s.model_fast,
        "model_deep": s.model_deep,
    }


@app.post("/events", response_model=EventOut, dependencies=[Depends(require_api_key)])
def ingest(event: EventIn) -> EventOut:
    s = get_settings()
    with span("api.ingest", event_kind=event.kind, subject=event.subject):
        run = start_run(kind=event.kind, subject=event.subject, metadata={"source": "api"})
        message_id = publish(
            s.topic_events,
            {"run_id": run.run_id, **event.model_dump()},
            run_id=run.run_id,
            kind=event.kind,
        )
        audit(
            action="event.ingested",
            actor="api",
            decision="accepted",
            run_id=run.run_id,
            kind=event.kind,
        )
        return EventOut(run_id=run.run_id, message_id=message_id, trace_id=current_trace_id())


# ── Read endpoints ───────────────────────────────────────────────────────────
#
# The UI polls these while a run is in flight. A full fleet run takes about a
# minute, and a screen that shows nothing for a minute reads as broken — so the
# timeline and the audit trail are queryable mid-run, not only at the end.
#
# All reads are behind the same API key as writes. The data is synthetic, but a
# system whose read path is unauthenticated has not modelled the boundary it
# claims to enforce.


@app.get("/runs", dependencies=[Depends(require_api_key)])
def list_runs(limit: int = 25) -> dict[str, Any]:
    query = (
        db()
        .collection("runs")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(min(limit, 100))
    )
    return {
        "runs": [{"run_id": doc.id, **(doc.to_dict() or {})} for doc in query.stream()],
    }


@app.get("/runs/{run_id}", dependencies=[Depends(require_api_key)])
def get_run(run_id: str) -> dict[str, Any]:
    doc = db().collection("runs").document(run_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail=f"no run {run_id}")

    checkpoints = [
        {"step_id": c.id, **(c.to_dict() or {})}
        for c in db().collection("runs").document(run_id).collection("checkpoints").stream()
    ]
    return {"run_id": run_id, **(doc.to_dict() or {}), "checkpoints": checkpoints}


@app.get("/audit", dependencies=[Depends(require_api_key)])
def list_audit(run_id: str | None = None, limit: int = 100) -> dict[str, Any]:
    """The reasoning trail. Filterable by run so the trace view can show one
    story rather than the whole log."""
    query = db().collection("audit")
    if run_id:
        query = query.where("details.run_id", "==", run_id)
    query = query.order_by("at", direction=firestore.Query.DESCENDING).limit(min(limit, 500))
    return {"entries": [{"id": d.id, **(d.to_dict() or {})} for d in query.stream()]}


@app.get("/approvals", dependencies=[Depends(require_api_key)])
def list_approvals(status: str = "pending") -> dict[str, Any]:
    query = db().collection("approvals").where("status", "==", status).limit(50)
    return {"approvals": [{"id": d.id, **(d.to_dict() or {})} for d in query.stream()]}


class ApprovalDecision(BaseModel):
    approved: bool
    decided_by: str = "caregiver"


@app.post("/approvals/{approval_id}", dependencies=[Depends(require_api_key)])
def decide_approval(approval_id: str, decision: ApprovalDecision) -> dict[str, Any]:
    """Record a human's decision.

    Deliberately does not execute anything: the run picks the settled approval up
    on its next tick. That way an approval granted while the worker is down is
    not lost, and a worker that comes back up twice does not act twice.
    """
    from vigil.actions import resolve_approval

    result = resolve_approval(approval_id, decision.approved, decision.decided_by)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("error"))
    return result


class PushEnvelope(BaseModel):
    """Pub/Sub push delivery. A 2xx response acks the message; anything else
    nacks it, and after five failures the dead-letter policy takes over."""

    message: dict[str, Any]
    subscription: str | None = None


@app.post("/pubsub/push", status_code=204)
async def pubsub_push(envelope: PushEnvelope) -> None:
    """Cloud counterpart of the local pull worker.

    Push is what keeps this deployment at zero cost when idle: a polling worker
    would need an always-warm instance, whereas this endpoint wakes the service
    only when there is an event. Both paths call the same handle_event, so the
    durability guarantees are identical.

    Authenticated by Cloud Run's OIDC check on the push service account, not by
    the X-API-Key header — hence no dependency on require_api_key here.
    """
    import base64
    import json

    from vigil.worker import handle_event

    raw = envelope.message.get("data", "")
    try:
        payload = json.loads(base64.b64decode(raw).decode())
    except (ValueError, TypeError) as exc:
        # Undecodable payloads must not be retried forever; ack and record.
        _log.error("push.undecodable", error=str(exc))
        audit("event.undecodable", actor="api", decision="dropped", error=str(exc))
        return

    await handle_event(payload)


# ── UI ───────────────────────────────────────────────────────────────────────
#
# Mounted last, and only at the root, so every API route above is matched first.
# Mounting a catch-all earlier would swallow /events and /runs into the static
# handler and return index.html for them — which fails in the least obvious way
# possible, as a 200 with the wrong body.
#
# Absent in local development, where the UI runs on its own dev server.
_UI_DIR = Path(__file__).resolve().parents[2] / "web" / "out"
if _UI_DIR.is_dir():
    app.mount("/", StaticFiles(directory=_UI_DIR, html=True), name="ui")
    _log.info("ui.mounted", path=str(_UI_DIR))
else:
    _log.info("ui.absent", path=str(_UI_DIR), note="run `make web` for the dev server")
