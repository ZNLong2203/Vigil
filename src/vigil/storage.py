"""Where uploaded artifacts live.

Three places, one interface:

    gs://bucket/path    Cloud Storage, which is where real uploads go
    fixtures/...        the committed synthetic corpus, resolved by bare filename
    .data/uploads/...   local uploads when there is no bucket to write to

The bare-filename case is not a convenience. The committed corpus is referenced
by name throughout the demo and the tests (`care-note-week3.pdf`), and those
references have to keep working whether or not a bucket exists — otherwise the
whole thing only runs on a configured cloud project, and the local path in the
README becomes a lie.

Uploads are content-addressed by hash. Dropping the same file twice produces the
same URI, so the run that follows claims the same idempotency key and is
recognised as a replay rather than doing the work again. That is the cheapest
possible deduplication and it falls out of naming things honestly.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path

from vigil.config import get_settings
from vigil.telemetry import log

_log = log("vigil.storage")

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "synthetic"
LOCAL_UPLOADS = Path(__file__).resolve().parents[2] / ".data" / "uploads"

#: Anything outside this set is refused at the door. An agent that can be handed
#: an arbitrary file type is an agent whose failure modes we have not enumerated.
ALLOWED = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".webm": "audio/webm",
    ".json": "application/json",
}

MAX_BYTES = 20 * 1024 * 1024

_SAFE = re.compile(r"[^A-Za-z0-9._-]")


class ArtifactRejected(Exception):
    """The upload was refused before anything touched storage."""


def _sanitise(filename: str) -> str:
    """Strip everything that could make a filename mean something to a path.

    Uploads are named by the client, and a client-supplied name is untrusted
    input like any other — `../../etc/passwd` is a filename too.
    """
    name = _SAFE.sub("_", Path(filename).name)
    return name[:120] or "artifact"


def put(filename: str, data: bytes, content_type: str | None = None) -> tuple[str, str]:
    """Store an artifact and return (uri, resolved_content_type)."""
    if len(data) > MAX_BYTES:
        raise ArtifactRejected(f"{len(data)} bytes exceeds the {MAX_BYTES} byte limit")

    safe = _sanitise(filename)
    suffix = Path(safe).suffix.lower()
    if suffix not in ALLOWED:
        raise ArtifactRejected(
            f"{suffix or 'no extension'} is not accepted. Allowed: {', '.join(sorted(ALLOWED))}"
        )

    resolved = content_type or ALLOWED[suffix]
    digest = hashlib.sha256(data).hexdigest()[:16]
    key = f"uploads/{digest}-{safe}"

    settings = get_settings()
    try:
        from google.cloud import storage as gcs

        client = gcs.Client(project=settings.project_id)
        bucket = client.bucket(settings.bucket_raw)
        blob = bucket.blob(key)
        blob.upload_from_string(data, content_type=resolved)
        uri = f"gs://{settings.bucket_raw}/{key}"
        _log.info("artifact.stored", uri=uri, bytes=len(data), content_type=resolved)
        return uri, resolved
    except Exception as exc:
        # No bucket, no credentials, or an emulator that does not implement the
        # call. Falling back keeps `make demo` working on a laptop; the log says
        # plainly which path was taken so nobody mistakes one for the other.
        LOCAL_UPLOADS.mkdir(parents=True, exist_ok=True)
        target = LOCAL_UPLOADS / f"{digest}-{safe}"
        target.write_bytes(data)
        _log.warning(
            "artifact.stored_locally",
            path=str(target),
            reason=str(exc)[:120],
            note="no bucket available",
        )
        return f"file://{target}", resolved


def get(uri: str) -> tuple[bytes, str]:
    """Read an artifact back. Returns (data, content_type)."""
    content_type = mimetypes.guess_type(uri)[0] or "application/octet-stream"

    if uri.startswith("gs://"):
        bucket_name, _, key = uri.removeprefix("gs://").partition("/")
        from google.cloud import storage as gcs

        client = gcs.Client(project=get_settings().project_id)
        blob = client.bucket(bucket_name).blob(key)
        return blob.download_as_bytes(), (blob.content_type or content_type)

    if uri.startswith("file://"):
        path = Path(uri.removeprefix("file://"))
        return path.read_bytes(), content_type

    # A bare name refers to the committed corpus.
    candidates = [FIXTURES / uri, FIXTURES / "photos" / uri, FIXTURES / "audio" / uri]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_bytes(), content_type

    raise FileNotFoundError(f"no artifact at {uri!r}")


def resolve(source_uri: str) -> tuple[bytes, str]:
    """Read by URI or by bare filename, trying the corpus last.

    A gs:// path that has expired or was never written falls through to the
    corpus by filename, which is what makes a demo recorded last week still run
    today from a fresh checkout.
    """
    try:
        return get(source_uri)
    except Exception:
        name = source_uri.rsplit("/", 1)[-1]
        return get(name)
