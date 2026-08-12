"""Idempotency-key properties.

These run with no cloud and no emulator, because the key is the one thing that
must never depend on the environment. If a key varied with dict ordering or with
the process that computed it, a resumed run would compute a *different* key,
find it unclaimed, and perform the side effect a second time — which is exactly
the failure the whole design exists to prevent.
"""

from __future__ import annotations

import pytest

from vigil.state import idempotency_key

PAYLOAD = {"subject": "care-subject-001", "amount": 42, "nested": {"b": 2, "a": 1}}


def test_key_is_deterministic():
    assert idempotency_key("run1", "step1", PAYLOAD) == idempotency_key("run1", "step1", PAYLOAD)


def test_key_ignores_dict_ordering():
    reordered = {"nested": {"a": 1, "b": 2}, "amount": 42, "subject": "care-subject-001"}
    assert idempotency_key("run1", "step1", PAYLOAD) == idempotency_key("run1", "step1", reordered)


@pytest.mark.parametrize(
    ("run_id", "step_id", "payload"),
    [
        ("run2", "step1", PAYLOAD),
        ("run1", "step2", PAYLOAD),
        ("run1", "step1", {**PAYLOAD, "amount": 43}),
    ],
)
def test_key_changes_when_anything_that_matters_changes(run_id, step_id, payload):
    assert idempotency_key(run_id, step_id, payload) != idempotency_key("run1", "step1", PAYLOAD)


def test_key_is_fixed_width():
    assert len(idempotency_key("run1", "step1", PAYLOAD)) == 32


def test_key_survives_a_process_boundary():
    """Recomputing in a fresh interpreter must give the same answer — the real
    resume path is a new process, not a new function call."""
    import json
    import subprocess
    import sys

    expected = idempotency_key("run1", "step1", PAYLOAD)
    code = (
        "import sys, json; sys.path.insert(0, 'src');"
        "from vigil.state import idempotency_key;"
        f"print(idempotency_key('run1', 'step1', json.loads({json.dumps(json.dumps(PAYLOAD))})))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == expected
