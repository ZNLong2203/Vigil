"""The weekly digest.

Offline. What is asserted is the contract around three optional renderers: that
a failure in one does not take the others with it, and that the result says what
is missing instead of quietly returning less than it promised.
"""

from __future__ import annotations

import pytest

from vigil import digest


@pytest.fixture(autouse=True)
def _no_credential(monkeypatch):
    digest._client.cache_clear()
    digest._music_client.cache_clear()
    monkeypatch.setattr(digest, "_client", lambda: None)
    monkeypatch.setattr(digest, "_music_client", lambda: None)


async def test_without_credentials_it_reports_everything_missing():
    result = await digest.build("care-subject-001", [])

    assert result.missing == ["text", "cue", "video"]
    assert "missing" in result.summary()


async def test_a_failed_video_does_not_take_the_text_with_it(monkeypatch):
    """The video takes minutes and is the most likely to fail. Losing the note a
    caregiver can actually read because a render timed out would be the wrong
    trade."""
    monkeypatch.setattr(digest, "summarise", lambda *a, **k: "Two things need you this week.")

    async def no_video(_text):
        return None

    async def a_cue(_urgency):
        return b"RIFF-cue"

    monkeypatch.setattr(digest, "render_video", no_video)
    monkeypatch.setattr(digest, "render_cue", a_cue)

    result = await digest.build("care-subject-001", [])

    assert result.text
    assert result.cues
    assert result.missing == ["video"]


async def test_the_cue_is_rendered_even_when_video_is_skipped(monkeypatch):
    """The cue answers "do I need to stop what I am doing" and costs seconds.
    The video is shareable and costs minutes. Skipping the expensive one must
    never skip the useful one."""
    monkeypatch.setattr(digest, "summarise", lambda *a, **k: "Nothing needs you.")

    async def a_cue(_urgency):
        return b"RIFF-cue"

    monkeypatch.setattr(digest, "render_cue", a_cue)

    result = await digest.build("care-subject-001", [], with_video=False)

    assert result.cues
    assert "video" not in result.missing


def test_every_urgency_level_has_its_own_prompt():
    """Three sounds a person can tell apart. If two levels shared a prompt they
    would sound the same and the whole mechanism would be decorative."""
    prompts = {digest.CUE_PROMPTS[u] for u in (digest.ROUTINE, digest.NEEDS_YOU, digest.URGENT)}
    assert len(prompts) == 3


def test_the_music_model_is_the_live_one_not_the_catalogue_one():
    """lyria-3-pro-preview is in models.list() and answers generateContent with
    notation, not audio. The model that streams audio is lyria-realtime-exp,
    which is not in the catalogue at all and needs the v1alpha endpoint."""
    assert digest.MUSIC_MODEL == "lyria-realtime-exp"
    assert digest.MUSIC_API_VERSION == "v1alpha"


def test_dates_survive_whatever_firestore_returns():
    """Firestore returns DatetimeWithNanoseconds, not a string, and the authored
    fixtures used ISO strings — so slicing `at[:10]` worked in every test and
    raised on the first real weekly digest. Correct everywhere except production
    is the shape this project keeps producing; this is the assertion that would
    have caught it."""
    from datetime import UTC, datetime

    assert digest._day("2026-08-12T08:00:00Z") == "2026-08-12"
    assert digest._day(datetime(2026, 8, 12, 8, 0, tzinfo=UTC)) == "2026-08-12"
    assert digest._day(None) == ""


def test_a_summary_survives_entries_with_no_details():
    """Audit entries written by a tool carry no `details` at all. `.get(...) or {}`
    rather than `.get(..., {})`: Firestore stores an explicit null, and the
    default only applies to a missing key."""
    from datetime import UTC, datetime

    events = [
        {"at": datetime(2026, 8, 12, tzinfo=UTC), "actor": "api", "action": "x", "details": None},
        {"at": "2026-08-11T00:00:00Z", "actor": "watchdog", "action": "y"},
    ]
    # No credential, so summarise returns "" — the assertion is that building the
    # prompt lines does not raise on either shape.
    assert digest.summarise("care-subject-001", events) == ""
