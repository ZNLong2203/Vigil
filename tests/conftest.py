"""Shared test helpers.

The important one is `emulator_reachable`. Guarding emulator tests on
`os.environ.get("FIRESTORE_EMULATOR_HOST")` looks right and is not: .env sets
that variable on every machine, so the guard passes whether or not Docker is
running. The tests then do not skip — they hang, retry, and eventually fail,
turning a one-second suite into a three-minute one and reporting a broken build
when nothing is broken.

Presence of configuration is not evidence of a running service. Open a socket.
"""

from __future__ import annotations

import os
import socket


def emulator_reachable(env_var: str) -> bool:
    """True only if something is actually listening at the configured address."""
    address = os.environ.get(env_var)
    if not address:
        return False

    host, _, port = address.rpartition(":")
    if not port.isdigit():
        return False

    try:
        with socket.create_connection((host or "localhost", int(port)), timeout=0.25):
            return True
    except OSError:
        return False


FIRESTORE_UP = emulator_reachable("FIRESTORE_EMULATOR_HOST")
PUBSUB_UP = emulator_reachable("PUBSUB_EMULATOR_HOST")
