"""Ingress. Accepts an event, publishes it, returns immediately.

The API never does agent work. It is the thin, always-fast tier; everything
expensive happens in the worker, off the request path. That separation is what
lets Cloud Run scale this to zero without stranding half-finished runs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field

from vigil import storage
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


@app.get("/ui-config")
def ui_config() -> dict[str, Any]:
    """The credential the bundled UI uses, handed over at runtime.

    The alternative was baking it into the JavaScript at image build time, which
    is where it was and which silently did not work: `gcloud run deploy --source`
    hands build env vars to the builder, not to Docker as build args, so the
    bundle shipped with an empty key. Nothing failed loudly. Every screen fell
    back to its fixtures and labelled itself "sample data" — exactly what it is
    designed to do when no backend answers — so the UI had never once been live
    in a browser and looked entirely healthy the whole time.

    Yes, this publishes the key, and that was already true by design: the service
    is --allow-unauthenticated, deploy.sh prints the key in plaintext, and a demo
    where a visitor drops in a photo and watches agents read it must carry a
    credential the visitor's browser can read. There is no arrangement in which a
    browser keeps a secret from the person using it. The key still does what its
    docstring claims — stops stray internet traffic from burning credits — and
    the real ceiling was never secrecy: --max-instances=3, the per-run token
    budget, and billing alerts.

    Unauthenticated on purpose. Requiring the key in order to fetch the key is a
    loop with no way in.
    """
    settings = get_settings()
    return {"api_key": settings.api_auth_key if settings.public_ui else None}


@app.post("/events", response_model=EventOut, dependencies=[Depends(require_api_key)])
def ingest(event: EventIn) -> EventOut:
    s = get_settings()
    with span("api.ingest", event_kind=event.kind, subject=event.subject):
        # source_uri travels on the run, not only in the queued message. Without
        # it a finished run cannot say which artifact it was about, so nothing
        # can pair the thing that arrived with the reading the agents made of it.
        run = start_run(
            kind=event.kind,
            subject=event.subject,
            metadata={"source": "api", "source_uri": event.source_uri, "body": event.body},
        )
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


class ArtifactOut(BaseModel):
    source_uri: str
    content_type: str
    bytes: int


@app.post("/artifacts", response_model=ArtifactOut, dependencies=[Depends(require_api_key)])
async def upload_artifact(file: UploadFile) -> ArtifactOut:
    """Store an uploaded photo, recording or document and return its URI.

    Upload and processing are separate calls on purpose. A caregiver dropping a
    photo should get an answer in the time it takes to store bytes, not the
    minute it takes three agents to read them — so this returns a URI, and the
    caller decides when to submit it as an event.

    Storage is content-addressed, so dropping the same file twice yields the same
    URI and the run that follows is recognised as a replay rather than repeating
    the work.
    """
    data = await file.read()
    try:
        uri, content_type = storage.put(
            file.filename or "artifact", data, file.content_type or None
        )
    except storage.ArtifactRejected as exc:
        # 415, not 400: the request was well-formed, we will not accept this type.
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    audit(
        "artifact.uploaded",
        actor="api",
        decision="accepted",
        source_uri=uri,
        content_type=content_type,
        bytes=len(data),
    )
    return ArtifactOut(source_uri=uri, content_type=content_type, bytes=len(data))


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


class DigestRequest(BaseModel):
    subject: str = "care-subject-001"
    days: int = 7
    #: Video takes minutes and the text takes seconds. A caller that wants an
    #: answer now asks for one without it.
    with_video: bool = False


@app.post("/digest", dependencies=[Depends(require_api_key)])
async def build_digest(request: DigestRequest) -> dict[str, Any]:
    """Assemble the week for one care subject.

    Called by Cloud Scheduler, not by a person. The digest is the one part of
    this system that is genuinely periodic — everything else reacts to an event —
    and a weekly note that has to be requested is a weekly note nobody reads.

    Returns the text and reports what could not be rendered. The video and cues
    are written to Cloud Storage rather than returned inline: a caregiver's
    phone should fetch fifteen seconds of video when it wants to, not receive it
    inside a JSON response.
    """
    from datetime import timedelta

    from vigil import digest as digest_module
    from vigil.state import now

    since = now() - timedelta(days=request.days)
    entries = [
        {"id": d.id, **(d.to_dict() or {})}
        for d in db().collection("audit").where("at", ">=", since).limit(200).stream()
    ]
    entries.sort(key=lambda e: str(e.get("at", "")))

    urgency = (
        digest_module.URGENT
        if any(e.get("decision") == "blocked" for e in entries)
        else digest_module.NEEDS_YOU
        if any(e.get("decision") in {"escalated", "awaiting_approval"} for e in entries)
        else digest_module.ROUTINE
    )

    result = await digest_module.build(
        request.subject, entries, urgency=urgency, with_video=request.with_video
    )

    stored: dict[str, str] = {}
    if result.video:
        uri, _ = storage.put(f"digest-{request.subject}.mp4", result.video, "video/mp4")
        stored["video"] = uri
    for level, audio in result.cues.items():
        uri, _ = storage.put(f"cue-{level}.wav", audio, "audio/wav")
        stored[f"cue_{level}"] = uri

    audit(
        "digest.built",
        actor="scheduler",
        decision="done",
        subject=request.subject,
        urgency=urgency,
        events=len(entries),
        missing=result.missing,
    )

    return {
        "subject": request.subject,
        "urgency": urgency,
        "events_considered": len(entries),
        "text": result.text,
        "artifacts": stored,
        "missing": result.missing,
    }


@app.get("/runs/{run_id}/trace", dependencies=[Depends(require_api_key)])
def get_trace(run_id: str) -> dict[str, Any]:
    """The reasoning chain for one run, as the trace view renders it.

    Assembled from the audit trail rather than from Cloud Trace. Both record the
    same run and they answer different questions: Cloud Trace has the timing and
    the spans, the audit log has the *decisions* — which boundary refused a call,
    why a step waited for a human. A caregiver looking at "why did this happen"
    needs the second. The OpenTelemetry spans are still exported and still the
    thing to open when the question is where the latency went.
    """
    run = db().collection("runs").document(run_id).get()
    if not run.exists:
        raise HTTPException(status_code=404, detail=f"no run {run_id}")

    run_data = run.to_dict() or {}
    entries = [
        {"id": d.id, **(d.to_dict() or {})}
        for d in db().collection("audit").where("details.run_id", "==", run_id).stream()
    ]
    entries.sort(key=lambda e: str(e.get("at", "")))

    checkpoints = [
        {"step_id": c.id, **(c.to_dict() or {})}
        for c in db().collection("runs").document(run_id).collection("checkpoints").stream()
    ]

    return {
        "run_id": run_id,
        "trace_id": run_data.get("trace_id"),
        "status": run_data.get("status"),
        "kind": run_data.get("kind"),
        "subject": run_data.get("subject"),
        "created_at": run_data.get("created_at"),
        "updated_at": run_data.get("updated_at"),
        "steps": sorted(checkpoints, key=lambda c: str(c.get("started_at", ""))),
        "entries": entries,
    }


@app.get("/registry", dependencies=[Depends(require_api_key)])
def get_registry() -> dict[str, Any]:
    """The catalogue, plus every version decision the eval gate has made.

    The entries come from code and the version history from Firestore, which is
    the honest split: what an agent *is* allowed to do is reviewed and deployed,
    while what happened when it tried to improve itself is a runtime record. A
    registry that let an agent widen its own scope at runtime would not be a
    boundary at all.

    Also returns, per agent, the tool names `build_belt` actually assembles for
    it, and who owns every scope in the system. Together those let a reader work
    out what an agent *cannot* reach — which is the claim the fleet screen makes,
    and which it previously illustrated with a hand-written denial event. That
    illustration was misleading in a specific way: a runtime denial is layer two,
    and layer two almost never fires, because layer one never hands the agent the
    tool in the first place. The boundary is real; the event was not the way to
    show it.
    """
    from vigil.fleet.registry import FLEET
    from vigil.fleet.scopes import SCOPE_OWNER
    from vigil.fleet.toolbelt import build_belt

    agents = []
    for entry in FLEET:
        versions = [
            {"id": doc.id, **(doc.to_dict() or {})}
            for doc in db()
            .collection("registry")
            .document(entry.name)
            .collection("versions")
            .stream()
        ]
        # Strip the instruction bodies: this endpoint is read by a browser, and
        # a version record carries the full replacement prompt.
        for version in versions:
            version.pop("instruction", None)
        versions.sort(key=lambda v: str(v.get("at", "")), reverse=True)

        agents.append(
            {
                "name": entry.name,
                "version": entry.version,
                "owner": str(entry.owner),
                "summary": entry.summary,
                "accepts": entry.capability_input,
                "returns": entry.capability_output,
                "tool_scopes": [str(s) for s in entry.tool_scopes],
                "callable_by": entry.callable_by,
                "eval": {
                    "suite": entry.eval.suite,
                    "score": entry.eval.score,
                    "cases": entry.eval.cases,
                    "anti_gaming_passed": entry.eval.anti_gaming_passed,
                },
                "versions": versions,
                "tools": sorted(t.name for t in build_belt(entry)),
            }
        )

    return {
        "agents": agents,
        # Scopes with no owner are infrastructure (reading the registry, writing
        # run state) and belong to no department.
        "scope_owners": {
            str(scope): (str(owner) if owner else None) for scope, owner in SCOPE_OWNER.items()
        },
    }


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
