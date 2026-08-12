"""Create the topics, subscription and bucket inside the local emulators.

Safe to run repeatedly — every operation is create-if-absent. The same code runs
against a real project, which is why deployment does not need a separate
provisioning script.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vigil.bus import ensure_subscription, ensure_topic  # noqa: E402
from vigil.config import get_settings  # noqa: E402


def main() -> int:
    s = get_settings()
    print(f"project           : {s.project_id}")
    print(f"firestore emulator: {s.firestore_emulator or '(real Firestore)'}")
    print(f"pubsub emulator   : {s.pubsub_emulator or '(real Pub/Sub)'}")
    print(f"storage emulator  : {s.storage_emulator or '(real GCS)'}")
    print()

    ensure_topic(s.topic_events)
    ensure_topic(s.topic_dlq)
    ensure_subscription(s.subscription_worker, s.topic_events, dlq_topic=s.topic_dlq)
    print(f"✓ topic        {s.topic_events}")
    print(f"✓ topic        {s.topic_dlq}  (dead letter)")
    print(f"✓ subscription {s.subscription_worker}")

    _ensure_bucket(s.bucket_raw, s.storage_emulator)
    return 0


def _ensure_bucket(name: str, emulator: str | None) -> None:
    """fake-gcs-server exposes a small management API; the real client library
    talks to it once STORAGE_EMULATOR_HOST is set, but creating the bucket over
    plain HTTP keeps this script dependency-free at startup."""
    import httpx

    if not emulator:
        from google.cloud import storage

        client = storage.Client()
        if not client.lookup_bucket(name):
            client.create_bucket(name)
        print(f"✓ bucket       {name}")
        return

    try:
        resp = httpx.post(f"{emulator}/storage/v1/b", json={"name": name}, timeout=10)
        if resp.status_code in (200, 409):
            print(f"✓ bucket       {name}")
        else:
            print(f"! bucket       {name} -> HTTP {resp.status_code} {resp.text[:120]}")
    except Exception as exc:
        print(f"! bucket       {name} -> {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
