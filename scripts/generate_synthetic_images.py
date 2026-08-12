"""Generate the photographic half of the synthetic corpus.

    uv run python scripts/generate_synthetic_images.py

Why generated rather than photographed: the corpus has to be synthetic anyway —
nothing here may depict a real person's medication or paperwork — and a generated
scene can be specified precisely for the property that matters, which is *how it
is hard to read*, not what it depicts.

Every prompt below is written for degradation, not for beauty. The failure mode
of an image model asked for "a photo of a label" is a clean product shot, which
would prove nothing: extraction from a crisp render is not evidence that the
system handles what a tired person actually sends. So each prompt names the
specific defect — the fold, the glare, the shadow across the text, the oblique
angle — and says "amateur snapshot, not a product photo" out loud.

Verified with the real pipeline: a generated note extracts at 0.90 confidence
with the reason "legible handwriting", which is the handwriting band from the
calibration table in agents.py. A clean render would have come back at 0.98 and
told us nothing.

These are committed, so `make demo` works without regenerating them and without
spending anything.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vigil.config import get_settings  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic" / "photos"

AMATEUR = (
    "Amateur smartphone snapshot taken in a hurry by someone with one hand free. "
    "Not a product photo, not styled, no studio lighting."
)

# Two failure modes worth naming explicitly, both found by looking at output.
#
# The first attempt at the appointment slip came back as a photo *of a phone
# screen* — notch, bezel, rounded corners and all. Asked for "a smartphone
# photo", the model rendered the smartphone. So the frame has to be ruled out in
# words.
#
# The second is subtler and is what makes an image read as AI: everything is
# centred, evenly lit and tidily composed. Real snapshots are none of those. A
# generated image is only useful here if it is hard to read, and "tidy" is the
# opposite of hard.
NOT_A_SCREENSHOT = (
    "The image is the photograph itself, filling the whole frame. No phone frame, "
    "no screen bezel, no notch, no rounded corners, no border, no UI, not a "
    "screenshot and not a photo of a screen."
)

UNPOSED = (
    "Composition is careless: the subject is off-centre and partly cut off by the "
    "edge of the frame, the camera is tilted, and the light is uneven — blown out "
    "where it falls directly, muddy and dark elsewhere."
)


@dataclass(frozen=True)
class Shot:
    filename: str
    difficulty: str
    prompt: str


SHOTS: list[Shot] = [
    Shot(
        "pill-note-01.png",
        "handwritten, creased, oblique angle, hand shadow across the text",
        "A close-up photo of a small scrap of white paper on a wooden kitchen table. "
        "Handwritten in blue ballpoint, slightly untidy: 'Synthecillin 5 mg - 1 daily "
        "with food'. The paper is creased and was folded twice. Shot at an oblique "
        "angle, not straight on. Dim indoor evening light from one side, the "
        f"photographer's hand casting a soft shadow across part of the text. {AMATEUR}",
    ),
    Shot(
        "pill-bottle-02.png",
        "curved label, glare, part of the text runs around the bottle",
        "A close-up photo of a plain amber pill bottle standing on a bathroom shelf. "
        "A white label is stuck on slightly crooked, handwritten in black marker: "
        "'Cardiolex 20mg - morning + night'. The bottle is cylindrical so the text "
        "curves away and the last word is partly hidden around the side. A bright "
        f"ceiling light reflects off the label as a hard white glare. {AMATEUR}",
    ),
    Shot(
        "blister-pack.png",
        "foil glare defeats naive OCR; small embossed print",
        "A close-up photo of a half-used silver blister pack of tablets lying on a "
        "dark countertop, several tablets already popped out. Small printed text on "
        "the foil reads 'FERROGEN 65mg'. Strong overhead light reflects off the foil "
        f"in broad white streaks across the printing. Slight motion blur. {AMATEUR}",
    ),
    Shot(
        "appointment-slip.png",
        "rushed handwriting on a crumpled slip, cramped at the edge, corner folded over",
        "A photo of a small crumpled paper slip, flattened out again, lying on a "
        "cluttered kitchen worktop next to a set of car keys and a coffee ring stain. "
        "Written fast in blue biro by someone not being careful: 'Follow-up - Dr "
        "Sandoval - Tues 14:30 - bring the lab result'. The handwriting is genuinely "
        "untidy: letters vary in size, the lines slope downwards to the right, and "
        "the last two words are cramped and squeezed in because the writer ran out of "
        "paper. Deep crease lines cut through the middle of the writing and the "
        "top-right corner is folded over, hiding part of a word. Harsh late-afternoon "
        f"sun through a window blows out the left third of the slip. {UNPOSED} "
        f"{AMATEUR} {NOT_A_SCREENSHOT}",
    ),
    Shot(
        "letter-scan.png",
        "printed letter photographed crooked, page curls, one corner in shadow",
        "A photo of a printed formal insurance letter lying on a table, photographed "
        "from above but noticeably crooked and slightly cut off at the bottom edge. "
        "The page curls up at one corner. The letterhead reads 'NORTHFIELD MUTUAL' "
        "and dense small paragraphs fill the page. Warm lamplight from the left "
        f"leaves the right side of the page in shadow. {AMATEUR}",
    ),
]


def main() -> int:
    settings = get_settings()
    if not settings.model_enabled:
        print("✗ No credentials. See scripts/check_models.py")
        return 1

    from google import genai

    # The image tier is separate from the reasoning tier and moves independently,
    # so it is not in Settings — override here if the id changes.
    model = os.environ.get("VIGIL_MODEL_IMAGE", "gemini-3-pro-image")
    client = genai.Client()
    OUT.mkdir(parents=True, exist_ok=True)

    print(f"model: {model}\nout  : {OUT}\n")
    written = 0

    for shot in SHOTS:
        target = OUT / shot.filename
        if target.exists() and not os.environ.get("VIGIL_REGENERATE"):
            print(f"· {shot.filename:24} exists (set VIGIL_REGENERATE=1 to replace)")
            continue

        try:
            response = client.models.generate_content(model=model, contents=shot.prompt)
        except Exception as exc:
            print(f"✗ {shot.filename:24} {str(exc)[:100]}")
            continue

        image = next(
            (
                part.inline_data.data
                for part in response.candidates[0].content.parts
                if getattr(part, "inline_data", None) and part.inline_data.data
            ),
            None,
        )
        if not image:
            print(f"✗ {shot.filename:24} model returned no image")
            continue

        target.write_bytes(image)
        written += 1
        print(f"✓ {shot.filename:24} {len(image) // 1024:>5} KB  — {shot.difficulty}")

    print(f"\n{written} written. All synthetic; no real person or record is depicted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
