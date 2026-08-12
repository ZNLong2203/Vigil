"""Render a weekly digest end to end, on camera.

    make digest

Writes to fixtures/synthetic/: the text, the video, and one cue per urgency
level. Each part is independent — a failure in one is reported and the rest still
render, which is the behaviour the digest is built around and the behaviour worth
showing.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from vigil.digest import NEEDS_YOU, ROUTINE, URGENT, build, render_cue

OUT = Path(__file__).resolve().parents[2] / "fixtures" / "synthetic"

#: A week that has something in it. Real audit entries have this shape; using a
#: fixed set keeps the demo reproducible and free of a Firestore round-trip.
WEEK = [
    {
        "at": "2026-08-04T11:05:00Z",
        "actor": "intake-agent",
        "action": "event.ingested",
        "decision": "done",
        "details": {"summary": "Home visit note read: Synthecillin 5 mg"},
    },
    {
        "at": "2026-08-06T14:20:00Z",
        "actor": "intake-agent",
        "action": "event.ingested",
        "decision": "done",
        "details": {"summary": "Insurer letter: Form CC-12 due 26 Aug"},
    },
    {
        "at": "2026-08-06T14:22:00Z",
        "actor": "watchdog",
        "action": "tool.denied",
        "decision": "denied",
        "details": {"summary": "benefits-agent refused clinical notes"},
    },
    {
        "at": "2026-08-09T08:40:00Z",
        "actor": "trust-boundary",
        "action": "guardrail.blocked",
        "decision": "blocked",
        "details": {"summary": "Injected instructions in a lab result"},
    },
    {
        "at": "2026-08-11T11:16:00Z",
        "actor": "watchdog",
        "action": "escalation.raised",
        "decision": "escalated",
        "details": {"summary": "Week 1 says 5 mg, week 3 says 10 mg"},
    },
    {
        "at": "2026-08-12T08:00:00Z",
        "actor": "benefits-agent",
        "action": "action.awaiting_approval",
        "decision": "awaiting_approval",
        "details": {"summary": "Form CC-12 drafted, needs you"},
    },
]


async def main() -> int:
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)

    digest = await build("care-subject-001", WEEK, urgency=NEEDS_YOU)

    print("=" * 74)
    print(digest.summary())
    print("=" * 74)

    if digest.text:
        (OUT / "weekly-digest.txt").write_text(digest.text + "\n")
        print(f"\n{digest.text}\n")

    if digest.video:
        (OUT / "weekly-digest.mp4").write_bytes(digest.video)
        print(f"video  {len(digest.video) // 1024:>6} KB  fixtures/synthetic/weekly-digest.mp4")

    # The other two levels, so all three can be compared side by side. This is
    # the point of the cues: they are only useful if they are distinguishable.
    cues = OUT / "cues"
    cues.mkdir(exist_ok=True)
    for urgency in (ROUTINE, NEEDS_YOU, URGENT):
        audio = digest.cues.get(urgency) or await render_cue(urgency)
        if audio:
            (cues / f"cue-{urgency}.wav").write_bytes(audio)
            print(f"cue    {len(audio) // 1024:>6} KB  fixtures/synthetic/cues/cue-{urgency}.wav")
        else:
            print(f"cue    {urgency}: unavailable")

    print(f"\n{time.monotonic() - started:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
