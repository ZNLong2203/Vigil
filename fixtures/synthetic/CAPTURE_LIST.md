# The synthetic corpus

Everything the demo runs on. **Nothing here depicts a real person, prescription
or record.** The medical content is deliberately generic — this is a
document-handling exercise, not clinical material.

All of it is generated and committed, so `make demo` works from a clean checkout
with nothing to shoot and nothing to spend.

```bash
uv run python scripts/generate_synthetic_data.py     # PDFs + JSON
uv run python scripts/generate_synthetic_images.py   # photos    (Gemini image)
uv run python scripts/generate_synthetic_audio.py    # voice notes (Gemini TTS)
```

Regenerate a file by deleting it, or set `VIGIL_REGENERATE=1` to replace them all.

## What each file is for

Every fixture exists to make one specific thing hard. A corpus of clean,
well-lit, monolingual documents would prove nothing: extraction from tidy input
is not evidence that the system handles what a tired person actually sends.

### Documents — `*.pdf`, `*.json`

| File | The difficulty | Verified behaviour |
|---|---|---|
| `benefits-letter.pdf` | The only real content is a date in the middle of paragraph three | Extraction must read the body, not scrape headers |
| `lab-result-tampered.pdf` | Prompt injection in white-on-white text, invisible on screen | **Blocked at the trust boundary in 287 ms in production**, and the clinical values were still extracted |
| `care-note-week1.pdf` / `care-note-week3.pdf` | 5 mg vs 10 mg, three weeks apart, neither acknowledging the other | Surfaced as a contradiction with both sources; never silently resolved |
| `medication-schedule.json` | Five medications collide at 08:00; Ferrogen and Osteoform D interact | Collision and interaction detection |
| `timeline-3-weeks.json` | Backdated history | Long-term memory has something to recall |

### Photos — `photos/*.png`

Generated rather than photographed. The corpus has to be synthetic either way,
and a generated scene can be specified for the property that matters — *how it is
hard to read* — rather than left to chance.

| File | The difficulty |
|---|---|
| `pill-note-01.png` | Handwriting on creased paper, oblique angle, hand shadow across the text |
| `pill-bottle-02.png` | Curved label so the text runs away around the bottle, hard glare |
| `blister-pack.png` | Foil glare in broad streaks; the small print is barely resolvable |
| `appointment-slip.png` | Rushed handwriting, deep creases, last words cramped, corner folded over |
| `letter-scan.png` | Printed letter shot crooked, page curling, one side in shadow |

Verified: `pill-note-01.png` extracts at **0.90 confidence** with the reason
*"legible handwriting"* — the handwriting band from the calibration table in
`agents.py`. A clean render would have come back at 0.98 and told us nothing.

### Voice notes — `audio/*.wav`

What makes a voice note hard is not the acoustics. Noise is the obvious thing to
reach for and it tests almost nothing; a transcript of a noisy recording is still
a transcript. These are hard in the ways that matter:

| File | The difficulty | Verified behaviour |
|---|---|---|
| `carer-note-01.wav` | Speaker is audibly unsure about a dose — *"ten milligrams? I think"* | Extracted at **0.50 confidence**, reason *"the speaker was unsure"*. Trips `approve.low_confidence`, so a human decides |
| `carer-note-02.wav` | Vietnamese and English inside one sentence | Detected `language=vi+en`; translated *"uống với đồ ăn"* → "take with food", *"thứ năm"* → Thursday, and inferred the family relationship from *con* / *mẹ* |
| `carer-note-03.wav` | Self-correction that supersedes an earlier fact | Feeds the contradiction path — the later statement does not silently win |

**Optional, two minutes:** for real room acoustics, play these through a phone
speaker and record them on another phone. The reverb is then genuine rather than
a synthesised approximation. Not required — the linguistic difficulty above is
what the system is actually being tested on.

## Checking the injection payload still works

```bash
uv run python -c "
from pypdf import PdfReader
t = PdfReader('fixtures/synthetic/lab-result-tampered.pdf').pages[0].extract_text()
print('injection extractable:', 'Ignore all previous instructions' in t)"
```

Open the same PDF in a viewer and confirm you cannot see it. That contrast is the
demo.
