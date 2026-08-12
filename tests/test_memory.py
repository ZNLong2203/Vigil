"""Contradiction detection.

Two ways this can be wrong, and they pull in opposite directions:

  - miss a real disagreement, and a dose changes because a scanner misread a
    digit and nobody was told;
  - report a disagreement that is only a formatting difference, and every
    document produces noise until the carer stops reading the alerts.

Both are failures. The normalisation tests are the second half of that, and they
matter as much as the first.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from vigil.memory import Claim, detect_contradictions, normalise

WEEK1 = Claim(
    field="synthecillin_dose",
    value="5 mg",
    confidence=0.94,
    source_uri="gs://vigil-raw/synthetic/care-note-week1.pdf",
    observed_at="2026-08-04T11:05:00Z",
)
WEEK3 = Claim(
    field="synthecillin_dose",
    value="10 mg",
    confidence=0.93,
    source_uri="gs://vigil-raw/synthetic/care-note-week3.pdf",
    observed_at="2026-08-19T11:15:00Z",
)


# ── Detection ────────────────────────────────────────────────────────────────


def test_finds_the_dose_disagreement():
    found = detect_contradictions([WEEK1, WEEK3])
    assert len(found) == 1
    assert set(found[0].values) == {"5 mg", "10 mg"}


def test_it_does_not_pick_a_winner():
    """The absent feature. Over three weeks of care notes a later document is
    routinely a transcription error, so preferring it would quietly change a
    dose. Both sides survive to the escalation."""
    contradiction = detect_contradictions([WEEK1, WEEK3])[0]
    assert not hasattr(contradiction, "winner")
    assert not hasattr(contradiction, "resolved_value")
    assert len(contradiction.claims) == 2


def test_the_description_carries_both_sources_and_dates():
    """A human settling this needs to know which document said what, and when.
    A bare "conflict detected" hands the work straight back to them."""
    text = detect_contradictions([WEEK1, WEEK3])[0].describe()
    assert "5 mg" in text and "10 mg" in text
    assert "care-note-week1.pdf" in text and "care-note-week3.pdf" in text
    assert "2026-08-04" in text and "2026-08-19" in text


def test_agreement_is_not_a_contradiction():
    same = replace(WEEK1, source_uri="gs://x/other.pdf")
    assert detect_contradictions([WEEK1, same]) == []


def test_one_source_disagreeing_with_itself_is_an_extraction_bug_not_a_conflict():
    """Same document read twice with different results is our pipeline's problem.
    Escalating it to a carer would be asking them to debug our OCR."""
    twice = replace(WEEK1, value="10 mg")
    assert twice.source_uri == WEEK1.source_uri
    assert detect_contradictions([WEEK1, twice]) == []


def test_unrelated_fields_do_not_collide():
    other = Claim(
        field="cardiolex_dose",
        value="20 mg",
        confidence=0.9,
        source_uri="gs://x/other.pdf",
        observed_at="2026-08-04T11:05:00Z",
    )
    assert [c.field for c in detect_contradictions([WEEK1, WEEK3, other])] == ["synthecillin_dose"]


def test_the_strongest_version_of_each_side_is_kept():
    weaker = replace(WEEK3, confidence=0.4, source_uri="gs://x/blurry.jpg")
    contradiction = detect_contradictions([WEEK1, WEEK3, weaker])[0]
    tens = [c for c in contradiction.claims if c.value == "10 mg"]
    assert len(tens) == 1
    assert tens[0].confidence == 0.93


# ── Normalisation: the false-positive half ───────────────────────────────────


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("5 mg", "5mg"),
        ("5 mg", "5 MG"),
        ("5 mg", "  5   mg  "),
        ("5.0 mg", "5 mg"),
    ],
)
def test_formatting_differences_are_the_same_claim(a, b):
    assert normalise(a) == normalise(b)


@pytest.mark.parametrize(("a", "b"), [("5 mg", "10 mg"), ("5 mg", "5 ml"), ("5 mg", "0.5 mg")])
def test_normalisation_never_collapses_a_real_difference(a, b):
    """Magnitude and unit are exactly the class of error this exists to catch.
    A normaliser that tidied "mg" and "ml" together would hide it."""
    assert normalise(a) != normalise(b)


def test_free_text_still_normalises_sensibly():
    assert normalise("  Once   Daily  ") == "once daily"
