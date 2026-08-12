"""Shared test helpers.

The important one is `firestore_usable`. Guarding emulator tests on
`os.environ.get("FIRESTORE_EMULATOR_HOST")` looks right and is not: .env sets
that variable on every machine, so the guard passes whether or not Docker is
running. The tests then do not skip — they hang, retry, and eventually fail,
turning a one-second suite into a three-minute one and reporting a broken build
when nothing is broken.

Presence of configuration is not evidence of a running service, and neither is
an open socket. Use the service.
"""

from __future__ import annotations

import os

import pytest


def firestore_usable() -> bool:
    """True only if a real Firestore read succeeds.

    This check has now been wrong three times, each at a level that looked
    sufficient:

        the env var is set          — .env sets it on every machine
        a socket opens              — Docker holds the forwarded port with
                                      nothing behind it
        something answers HTTP      — a Firebase Emulator UI from an unrelated
                                      project was on 8080, answering happily and
                                      serving no Firestore at all

    Every version was a proxy for "is the service there". The only answer that is
    not a proxy is to use the service. It costs a few milliseconds once.
    """
    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        return False

    try:
        from vigil.state import db

        next(db().collection("_probe").limit(1).stream(retry=None, timeout=2.0), None)
        return True
    except Exception:
        return False


FIRESTORE_UP = firestore_usable()


@pytest.fixture(autouse=True)
def _offline_by_default(monkeypatch):
    """No test reaches a model unless it asks to.

    The trust boundary calls the Gemma redaction tier, and the moment it did the
    suite went from two seconds to ninety-five — every guardrail test was quietly
    making network calls. Adding a model to a shared code path turns an offline
    suite into an integration suite without anyone deciding to.

    Tests that want the model path override this fixture themselves.
    """
    from vigil import redaction

    redaction._client.cache_clear()
    monkeypatch.setattr(redaction, "_client", lambda: None)
