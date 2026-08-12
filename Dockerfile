# One image, one URL: the API and the UI ship together.
#
# A judge should be able to open a single link and see the system, not assemble
# it from a backend host and a frontend host. The UI is a static export (no SSR,
# see web/next.config.ts), so serving it from the API container costs one COPY
# and removes a whole deployment.

# ── UI build ─────────────────────────────────────────────────────────────────
#
# Alpine rather than slim: nothing from this stage reaches the runtime image
# except the static output, but a build stage still executes with the source
# tree in front of it, so a smaller attack surface during build is worth the one
# word. Only /ui/out is copied forward.
FROM node:22-alpine AS ui

WORKDIR /ui
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY web/ ./
# Baked in at build time: a static export has no server to read env vars at
# runtime. Same-origin by default, so the UI calls the API it was served from.
ARG NEXT_PUBLIC_VIGIL_API=""
ARG NEXT_PUBLIC_VIGIL_KEY=""
ENV NEXT_PUBLIC_VIGIL_API=$NEXT_PUBLIC_VIGIL_API
ENV NEXT_PUBLIC_VIGIL_KEY=$NEXT_PUBLIC_VIGIL_KEY
RUN npm run build

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first: this layer is cached across code changes, which is the
# difference between a 20-second redeploy and a 3-minute one.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
RUN uv sync --frozen --no-dev

# The synthetic corpus ships with the image.
#
# In production these artifacts arrive in Cloud Storage and the tools read them
# from there; baking them in is a demo affordance, so a reviewer can exercise the
# whole pipeline — including the tampered PDF that the trust boundary blocks —
# without first uploading anything. tools.py resolves them relative to /app, so
# the path has to match the layout above.
COPY fixtures/ ./fixtures/

COPY --from=ui /ui/out ./web/out

# Cloud Run injects PORT. Never hardcode 8080 here.
ENV PORT=8080
EXPOSE 8080

# Non-root: least privilege applies to the container too, not just the agents.
RUN useradd --create-home --uid 1001 vigil && chown -R vigil:vigil /app
USER vigil

CMD exec uvicorn vigil.api:app --host 0.0.0.0 --port ${PORT} --app-dir src
