"""The Gemma redaction tier.

Offline. What is asserted here is the contract around the model, not the model:
that it degrades loudly rather than silently, and that it cannot destroy the
clinical values it was brought in to protect.
"""

from __future__ import annotations

from vigil import redaction


def test_without_a_credential_it_says_so_rather_than_pretending():
    """A redaction step that silently degrades to nothing is worse than none:
    everything downstream keeps believing it happened."""
    result = redaction.redact("Write to a@b.test about policy NM-SYNTH-4471-B.")

    assert result.used_model is False
    assert "names require the model tier" in result.note
    assert "a@b.test" not in result.text


def test_the_regex_tier_still_runs_when_the_model_is_absent():
    result = redaction.redact("Contact carer@example.test, ref NM-SYNTH-4471-B.")
    assert result.count == 2
    assert "[EMAIL_1]" in result.text


def test_a_model_failure_degrades_loudly(monkeypatch):
    class Exploding:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                raise RuntimeError("upstream is down")

    monkeypatch.setattr(redaction, "_client", lambda: Exploding())

    result = redaction.redact("Write to a@b.test.")

    assert result.used_model is False
    assert "unavailable" in result.note
    assert "a@b.test" not in result.text, "the regex tier must still have run"


def test_the_model_cannot_redact_a_dosage(monkeypatch):
    """A redactor that eats the dose has destroyed the record it was protecting,
    and extraction downstream would report a confident value for '[ID_1] mg'."""

    class Overzealous:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                class R:
                    text = (
                        '{"spans": [{"text": "5 mg", "kind": "ID"},'
                        ' {"text": "A. Rivera", "kind": "PERSON"}]}'
                    )

                return R()

    monkeypatch.setattr(redaction, "_client", lambda: Overzealous())

    result = redaction.redact("A. Rivera takes Synthecillin 5 mg once daily.")

    assert "5 mg" in result.text, "clinical values must survive redaction"
    assert "A. Rivera" not in result.text
    assert "[PERSON_1]" in result.text


def test_spans_the_model_invents_are_ignored(monkeypatch):
    """The model returns spans copied from the text. One that is not actually
    present is a hallucination, and replacing on it would corrupt the document."""

    class Inventive:
        class models:
            @staticmethod
            def generate_content(**_kwargs):
                class R:
                    text = '{"spans": [{"text": "Someone Not Here", "kind": "PERSON"}]}'

                return R()

    monkeypatch.setattr(redaction, "_client", lambda: Inventive())

    original = "A. Rivera takes Synthecillin."
    assert redaction.redact(original).text == original
