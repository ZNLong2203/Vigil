"""Golden sets.

Inside the package rather than in a top-level `evals/` directory so they ship
with the image. The Dockerfile copies `src/`, and a suite that lives outside it
is a suite that is missing in production — the same way pypdf was missing when
it was a dev dependency, and for the same reason.
"""
