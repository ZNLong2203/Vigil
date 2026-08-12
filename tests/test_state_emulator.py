"""Exactly-once behaviour against the Firestore emulator.

Skipped unless the emulator is running (`make up`), so `make test` stays green
on a machine with no Docker.

This is the automated form of the chaos demo: claim a step, do not complete it —
simulating a process that died between the checkpoint and the side effect — then
claim it again and assert the second attempt is refused.
"""

from __future__ import annotations

import uuid

import pytest
from tests.conftest import FIRESTORE_UP

# A real read, not a proxy for one. See conftest.firestore_usable — three
# cheaper checks each looked sufficient and each was wrong.
pytestmark = pytest.mark.skipif(
    not FIRESTORE_UP,
    reason="Firestore emulator is not listening — run `make up` first",
)


@pytest.fixture()
def run_id() -> str:
    return f"test-{uuid.uuid4().hex[:12]}"


def test_second_claim_of_the_same_step_is_refused(run_id):
    from vigil.state import StepAlreadyDone, claim_step

    payload = {"action": "file_benefits_claim", "reference": "SYNTH-0001"}
    claim_step(run_id, "submit", payload)

    with pytest.raises(StepAlreadyDone):
        claim_step(run_id, "submit", payload)


def test_completed_step_stays_claimed(run_id):
    from vigil.state import StepAlreadyDone, claim_step, complete_step

    payload = {"action": "book_appointment", "slot": "2026-09-02T09:00:00Z"}
    key = claim_step(run_id, "book", payload)
    complete_step(run_id, "book", key, {"confirmation": "SYNTH-A1"})

    with pytest.raises(StepAlreadyDone):
        claim_step(run_id, "book", payload)


def test_failed_step_releases_the_claim_for_a_genuine_retry(run_id):
    """A step that failed before touching the outside world must be retryable.
    Poisoning the key forever would turn a transient error into a stuck run."""
    from vigil.state import claim_step, fail_step

    payload = {"action": "send_reminder", "channel": "sms"}
    key = claim_step(run_id, "remind", payload)
    fail_step(run_id, "remind", key, "upstream timeout")

    assert claim_step(run_id, "remind", payload)  # succeeds — no exception


def test_different_payload_is_a_different_step(run_id):
    from vigil.state import claim_step

    claim_step(run_id, "order", {"item": "pill organiser", "qty": 1})
    assert claim_step(run_id, "order", {"item": "pill organiser", "qty": 2})
