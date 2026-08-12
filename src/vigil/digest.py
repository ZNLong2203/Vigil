"""The weekly digest: what the fleet did, in forms a tired person will actually take in.

A caregiver who has been away for a week does not read a forty-line timeline.
This turns the week into three artifacts, each earning its place differently:

    text   Gemini writes six sentences a person can read standing up
    video  Veo renders those sentences as something shareable — a sibling who
           also cares, or the clinic at the next appointment, will watch fifteen
           seconds and will not scroll an audit log
    cue    Lyria generates short distinct signatures per urgency level, so a
           notification can be told apart without looking at the screen

The cue is the one that matters most and looks least impressive. A caregiver's
hands are usually full — changing a dressing, driving, holding someone up — and
"do I need to stop what I am doing" is the only question a notification has to
answer in that moment. A colour or a badge cannot answer it. Three sounds can.

Everything here is optional. A digest that fails to render a video still returns
its text, and says which parts are missing rather than pretending they were never
asked for.
"""

from __future__ import annotations

import asyncio
import time
import wave
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from vigil.config import get_settings
from vigil.telemetry import log, span

_log = log("vigil.digest")

VIDEO_MODEL = "veo-3.1-fast-generate-preview"

# Not `lyria-3-pro-preview`, and not discoverable.
#
# The catalogue lists lyria-3-pro-preview and lyria-3-clip-preview; both answer
# generateContent with music *notation* (`[[A0]] [[B1]]`), not audio, and the
# Live Music socket rejects them as not found. The model that actually streams
# audio is lyria-realtime-exp, which does not appear in models.list() at all —
# Live API models are not in the REST catalogue, so `make models` cannot show it.
#
# It also needs the v1alpha endpoint. On v1beta and v1 the socket 404s outright.
MUSIC_MODEL = "lyria-realtime-exp"
MUSIC_API_VERSION = "v1alpha"

#: Lyria streams PCM continuously; this is how long we listen before stopping.
CUE_SECONDS = 4.0
MUSIC_SAMPLE_RATE = 48_000
MUSIC_CHANNELS = 2

VIDEO_TIMEOUT_S = 300


class Urgency(str):
    """Three levels, because a person can reliably tell three sounds apart and
    cannot reliably tell five."""


ROUTINE = "routine"
NEEDS_YOU = "needs_you"
URGENT = "urgent"

#: Written as musical direction rather than emotion. "Calm" is not a sound; a
#: single low chime with a long decay is.
CUE_PROMPTS: dict[str, str] = {
    ROUTINE: (
        "One soft low marimba note with a long natural decay. Warm, unhurried, "
        "resolved. Nothing follows it."
    ),
    NEEDS_YOU: (
        "Two clear mid-range bell tones rising a whole step, gentle but definite, "
        "leaving the phrase open and unresolved."
    ),
    URGENT: (
        "Three short repeated tones at a steady quick pulse, bright and insistent, "
        "unmistakably asking for attention without alarm or harshness."
    ),
}

SUMMARY_INSTRUCTION = """
You write a weekly note for someone caring for a family member at home. They
have been busy and have not looked at the app.

Six sentences at most. Lead with anything that needs them — an approval waiting,
a contradiction nobody has settled. Then what was handled, briefly. Then what is
coming.

Write the way a colleague would speak, not the way a report reads. No headings,
no bullet points, no jargon, no reassurance they did not ask for. If nothing
needs them, say so first and plainly.
""".strip()


@dataclass
class Digest:
    subject: str
    text: str = ""
    video: bytes | None = None
    cues: dict[str, bytes] = field(default_factory=dict)
    urgency: str = ROUTINE
    missing: list[str] = field(default_factory=list)

    def summary(self) -> str:
        have = ["text" if self.text else None, "video" if self.video else None]
        have.append(f"{len(self.cues)} cues" if self.cues else None)
        parts = [p for p in have if p]
        line = f"{self.subject}: {', '.join(parts) or 'nothing rendered'} · {self.urgency}"
        return f"{line} · missing {', '.join(self.missing)}" if self.missing else line


@lru_cache(maxsize=1)
def _client() -> Any | None:
    """The Gemini API client. Veo and Lyria are not served by Vertex, so this is
    the same second credential the redaction tier uses — see ADR 005."""
    settings = get_settings()
    if not settings.gemma_api_key:
        return None
    from google import genai

    return genai.Client(api_key=settings.gemma_api_key, vertexai=False)


@lru_cache(maxsize=1)
def _music_client() -> Any | None:
    """A third client, pinned to v1alpha, purely for the Live Music socket.

    Three clients in one process is not tidy, and each one exists because a
    different surface needs a different thing: Vertex for the reasoning tier by
    identity, the Gemini API for models Vertex does not serve, and v1alpha for a
    socket that only exists there. Sharing one would break two of them.
    """
    settings = get_settings()
    if not settings.gemma_api_key:
        return None
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=settings.gemma_api_key,
        vertexai=False,
        http_options=types.HttpOptions(api_version=MUSIC_API_VERSION),
    )


def _day(value: Any) -> str:
    """Just the date, from whatever the caller had.

    Firestore returns DatetimeWithNanoseconds, not a string, and slicing one
    raises. The authored fixtures used ISO strings, so this only ever failed
    against real data — the same shape of bug as a dev-only dependency: correct
    everywhere except production.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value[:10]
    return getattr(value, "date", lambda: value)().isoformat()[:10]


def summarise(subject: str, events: list[dict[str, Any]], *, urgency: str = ROUTINE) -> str:
    """Six sentences from the week's audit entries."""
    from google.genai import types

    client = _client()
    if client is None:
        return ""

    lines = "\n".join(
        f"- {_day(e.get('at'))} {e.get('actor', '')}: {e.get('action', '')} "
        f"({e.get('decision', '')}) {str((e.get('details') or {}).get('summary', ''))[:120]}"
        for e in events[:80]
    )
    response = client.models.generate_content(
        model=get_settings().model_fast,
        contents=f"This week for {subject}:\n\n{lines}",
        config=types.GenerateContentConfig(system_instruction=SUMMARY_INSTRUCTION),
    )
    return (response.text or "").strip()


async def render_cue(urgency: str) -> bytes | None:
    """Generate one urgency signature with Lyria.

    Lyria is a *streaming* model — it does not return a clip, it plays until you
    stop listening. So this opens a session, sets the prompt, collects audio for
    a few seconds and closes. The awkwardness is inherent to the model, not to
    the use: what we want is a four-second cue and what it offers is an endless
    performance.
    """
    from google.genai import types

    client = _music_client()
    if client is None:
        return None

    prompt = CUE_PROMPTS.get(urgency, CUE_PROMPTS[ROUTINE])
    chunks: list[bytes] = []

    try:
        async with client.aio.live.music.connect(model=MUSIC_MODEL) as session:
            await session.set_weighted_prompts(
                prompts=[types.WeightedPrompt(text=prompt, weight=1.0)]
            )
            await session.set_music_generation_config(
                config=types.LiveMusicGenerationConfig(bpm=72, temperature=0.9)
            )
            await session.play()

            deadline = time.monotonic() + CUE_SECONDS
            async for message in session.receive():
                chunk = getattr(getattr(message, "server_content", None), "audio_chunks", None)
                if chunk:
                    chunks.append(chunk[0].data)
                if time.monotonic() > deadline:
                    break
            await session.stop()
    except Exception as exc:
        _log.warning("digest.cue_failed", urgency=urgency, error=str(exc)[:160])
        return None

    if not chunks:
        return None

    import io

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(MUSIC_CHANNELS)
        handle.setsampwidth(2)
        handle.setframerate(MUSIC_SAMPLE_RATE)
        handle.writeframes(b"".join(chunks))
    return buffer.getvalue()


async def render_video(text: str) -> bytes | None:
    """Render the week as a short shareable clip with Veo.

    Veo is a long-running operation rather than a call: it returns a handle and
    is polled. Minutes, not seconds — so this is never on the request path. The
    digest is produced on a schedule and the video attaches when it is ready.
    """
    client = _client()
    if client is None or not text:
        return None

    prompt = (
        "A calm, warm domestic scene in soft natural daylight: a tidy kitchen table with "
        "a pill organiser, a paper calendar and a cup of tea. Slow gentle camera drift. "
        "Nobody is in frame. Unhurried and reassuring, documentary in feel, no text and "
        "no writing anywhere in the image."
    )

    try:
        operation = client.models.generate_videos(model=VIDEO_MODEL, prompt=prompt)
        deadline = time.monotonic() + VIDEO_TIMEOUT_S

        while not operation.done:
            if time.monotonic() > deadline:
                _log.warning("digest.video_timeout", seconds=VIDEO_TIMEOUT_S)
                return None
            await asyncio.sleep(10)
            operation = client.operations.get(operation)

        generated = operation.response.generated_videos[0]
        client.files.download(file=generated.video)
        return generated.video.video_bytes
    except Exception as exc:
        _log.warning("digest.video_failed", error=str(exc)[:160])
        return None


async def build(
    subject: str,
    events: list[dict[str, Any]],
    *,
    urgency: str = ROUTINE,
    with_video: bool = True,
) -> Digest:
    """Assemble the week. Each part is optional and says so when it is absent."""
    digest = Digest(subject=subject, urgency=urgency)

    with span("digest.build", subject=subject, urgency=urgency):
        digest.text = summarise(subject, events, urgency=urgency)
        if not digest.text:
            digest.missing.append("text")

        # The cue matters more than the video and costs seconds rather than
        # minutes, so it is rendered first and never skipped.
        cue = await render_cue(urgency)
        if cue:
            digest.cues[urgency] = cue
        else:
            digest.missing.append("cue")

        if with_video:
            video = await render_video(digest.text)
            if video:
                digest.video = video
            else:
                digest.missing.append("video")

    _log.info("digest.built", summary=digest.summary())
    return digest
