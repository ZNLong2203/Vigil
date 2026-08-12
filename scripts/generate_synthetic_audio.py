"""Generate the voice-note half of the synthetic corpus.

    uv run python scripts/generate_synthetic_audio.py

What actually makes a voice note hard is not the acoustics. Background noise is
the obvious thing to reach for and it tests almost nothing — a transcript of a
noisy recording is still a transcript. The properties that exercise this system
are linguistic, and they are all in the script:

  hesitation      "the nurse said ten milligrams? I think" — the speaker is not
                  sure, so the extraction must not be either. This is what drives
                  the confidence band down to 0.4 and trips approve.low_confidence
                  in the policy engine.
  code-switching  Vietnamese and English inside one sentence, which is how a
                  bilingual household actually speaks and is exactly the
                  "unusual, messy" input the brief asks for.
  self-correction "ignore what I said about Tuesday" — a later statement that
                  supersedes an earlier one, which is the contradiction case the
                  watchdog has to surface rather than silently resolve.

None of those need a microphone. If you want real room acoustics on top, play
these through a phone speaker and record them on another phone: two minutes, and
the reverb is genuine rather than a synthesised approximation.

Output is 24 kHz mono PCM wrapped as WAV, which is what the TTS models return.
"""

from __future__ import annotations

import os
import sys
import wave
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vigil.config import get_settings  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic" / "audio"

SAMPLE_RATE = 24_000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit


@dataclass(frozen=True)
class Note:
    filename: str
    voice: str
    tests: str
    #: Delivery instructions come first — the TTS models follow a stage direction
    #: at the top of the prompt, and a flat reading would lose the hesitation
    #: that the whole fixture exists to carry.
    direction: str
    script: str


NOTES: list[Note] = [
    Note(
        "carer-note-01.wav",
        voice="Kore",
        tests="hesitation and an uncertain dose — should extract at low confidence",
        direction=(
            "Read this as a tired person recording a quick voice memo for themselves in a "
            "hospital corridor. Rushed, thinking aloud, genuinely unsure in the middle. "
            "Let the uncertain parts trail upward like a question."
        ),
        script=(
            "Um, so the nurse came this morning — she said the Synthecillin goes up to ten "
            "milligrams? I think. I should check that. And we still haven't sent that "
            "C C twelve form, the deadline's coming up soon."
        ),
    ),
    Note(
        "carer-note-02.wav",
        voice="Puck",
        tests="Vietnamese and English switching inside one sentence",
        direction=(
            "Read this as a bilingual Vietnamese speaker talking to a family member, "
            "switching between Vietnamese and English mid-sentence without pausing at the "
            "switch. Natural and unselfconscious, not careful."
        ),
        script=(
            "Mẹ ơi, cái thuốc buổi sáng ấy — the nurse said uống với đồ ăn nhé, "
            "with food, không được uống lúc đói. Rồi cái appointment thứ Năm này, "
            "con sẽ đưa mẹ đi."
        ),
    ),
    Note(
        "carer-note-03.wav",
        voice="Charon",
        tests="self-correction that supersedes an earlier fact",
        direction=(
            "Read this as someone who has just realised they got something wrong and is "
            "correcting it quickly, slightly apologetic, in a hurry."
        ),
        script=(
            "Sorry — ignore what I said about Tuesday. They moved it to Thursday, "
            "same time, half past two. Thursday, not Tuesday."
        ),
    ),
]


def write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)


def main() -> int:
    settings = get_settings()
    if not settings.model_enabled:
        print("✗ No credentials. See scripts/check_models.py")
        return 1

    from google import genai
    from google.genai import types

    model = os.environ.get("VIGIL_MODEL_TTS", "gemini-2.5-flash-tts")
    client = genai.Client()
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"model: {model}\nout  : {OUT}\n")
    written = 0

    for note in NOTES:
        target = OUT / note.filename
        if target.exists() and not os.environ.get("VIGIL_REGENERATE"):
            print(f"· {note.filename:22} exists (set VIGIL_REGENERATE=1 to replace)")
            continue

        try:
            response = client.models.generate_content(
                model=model,
                contents=f"{note.direction}\n\n{note.script}",
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=note.voice)
                        )
                    ),
                ),
            )
            pcm = response.candidates[0].content.parts[0].inline_data.data
        except Exception as exc:
            print(f"✗ {note.filename:22} {str(exc)[:100]}")
            continue

        write_wav(target, pcm)
        seconds = len(pcm) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)
        written += 1
        print(f"✓ {note.filename:22} {seconds:4.1f}s  {note.voice:8} — {note.tests}")

    print(f"\n{written} written. All synthetic; no real person is recorded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
