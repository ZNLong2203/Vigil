"""Confirm credentials work, and list the model ids this account can actually use.

Run this the moment a key is in place:

    uv run python scripts/check_models.py

Model ids move faster than any documentation, and the hackathon requires Gemini
3.5 or newer — so the ids in .env are a guess until this says otherwise. Copy the
exact strings it prints into VIGIL_MODEL_FAST and VIGIL_MODEL_DEEP.

Works for both auth paths:
    GOOGLE_API_KEY=...                  Google AI Studio
    GOOGLE_GENAI_USE_VERTEXAI=true      Vertex AI (uses application-default creds)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vigil.config import get_settings  # noqa: E402


def main() -> int:
    settings = get_settings()
    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"1", "true", "yes"}

    print(f"auth path : {'Vertex AI' if use_vertex else 'Gemini API (AI Studio)'}")
    print(f"project   : {settings.project_id}")
    print(f"configured: fast={settings.model_fast}  deep={settings.model_deep}")
    print()

    if not settings.model_enabled:
        print("✗ No credentials found.")
        print("  Either set GOOGLE_API_KEY in .env (aistudio.google.com → Get API key),")
        print("  or set GOOGLE_GENAI_USE_VERTEXAI=true and run:")
        print("      gcloud auth application-default login")
        return 1

    try:
        from google import genai
    except ImportError:
        print("✗ google-genai is not installed. Run: uv sync")
        return 1

    client = genai.Client()

    try:
        models = list(client.models.list())
    except Exception as exc:
        print(f"✗ Could not reach the API: {exc}")
        print("  A 401/403 usually means the key is wrong or the API is not enabled.")
        return 1

    # Group by prefix rather than by supported action. Filtering on
    # generateContent hides Veo, Imagen and the embedding models, which use
    # different methods — and those are exactly the ones the bonus points and the
    # vector memory depend on.
    # Vertex returns "publishers/google/models/gemini-2.5-flash"; the Gemini API
    # returns "models/gemini-2.5-flash". Take the last segment either way.
    names = sorted({(m.name or "").rsplit("/", 1)[-1] for m in models if m.name})
    print(f"✓ Credentials work — {len(names)} models visible")

    groups: list[tuple[str, list[str]]] = [
        (
            "Gemini (the mandatory tier — must be 3.5 or newer)",
            [n for n in names if n.startswith("gemini") and "embedding" not in n],
        ),
        (
            "Gemma  (bonus +0.2 · local redaction and routing)",
            [n for n in names if n.startswith("gemma")],
        ),
        ("Veo    (bonus +0.2 · weekly video digest)", [n for n in names if n.startswith("veo")]),
        ("Lyria  (bonus +0.2 · audio digest)", [n for n in names if n.startswith("lyria")]),
        ("Embeddings (episodic memory)", [n for n in names if "embedding" in n]),
    ]
    listed = {n for _, group in groups for n in group}

    for title, group in groups:
        if not group:
            print(f"\n{title}\n  (none available on this key)")
            continue
        print(f"\n{title}")
        for name in group:
            marks = []
            if name == settings.model_fast:
                marks.append("← VIGIL_MODEL_FAST")
            if name == settings.model_deep:
                marks.append("← VIGIL_MODEL_DEEP")
            print(f"  {name:44} {' '.join(marks)}")

    if rest := [n for n in names if n not in listed]:
        print("\nOther")
        for name in rest:
            print(f"  {name}")

    print()
    ok = True
    for label, configured in (("fast", settings.model_fast), ("deep", settings.model_deep)):
        if configured not in names:
            ok = False
            print(f"⚠ VIGIL_MODEL_{label.upper()} = {configured!r} is NOT available on this key.")
            print("  Pick an explicit id from above and update .env.")
        elif not _is_recent_enough(configured):
            ok = False
            print(f"⚠ VIGIL_MODEL_{label.upper()} = {configured!r} looks older than Gemini 3.5,")
            print("  which would fail the hackathon's mandatory requirement.")

    if ok:
        print("✓ Both configured models exist and satisfy 'Gemini 3.5 or newer'.")
    return 0


def _is_recent_enough(model_id: str) -> bool:
    """Best-effort version check against the mandatory 'Gemini 3.5 or newer'.

    Aliases like gemini-pro-latest carry no version, so they cannot be evidenced
    in a compliance table and are treated as failing — better a false warning
    than a submission rejected at the pass/fail stage.
    """
    import re

    match = re.match(r"gemini-(\d+)(?:\.(\d+))?", model_id)
    if not match:
        return True  # not a Gemini model; the rule does not apply
    major, minor = int(match.group(1)), int(match.group(2) or 0)
    return (major, minor) >= (3, 5)


if __name__ == "__main__":
    raise SystemExit(main())
