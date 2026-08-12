"""Runtime configuration.

One rule here: the same code path runs locally and on Cloud Run. The only thing
that changes is whether the *_EMULATOR_HOST variables are set, which the Google
client libraries pick up on their own. Nothing branches on "am I in the cloud"
beyond reporting it on the health endpoint.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env into the real process environment, not just into Settings.
#
# pydantic-settings can read a .env file on its own, but it populates the model
# and stops there. The Google SDKs — google-genai, ADK, and the Firestore and
# Pub/Sub clients looking for *_EMULATOR_HOST — all read os.environ directly, so
# a value that only exists on the Settings object is invisible to every library
# that actually needs it.
#
# override=False so a variable set by Cloud Run wins over a stale local file.
load_dotenv(override=False)


class Settings(BaseSettings):
    # protected_namespaces=() because several fields are legitimately named
    # model_* and pydantic reserves that prefix by default.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    env: str = Field(default="local", validation_alias="VIGIL_ENV")
    project_id: str = Field(default="vigil-local", validation_alias="GOOGLE_CLOUD_PROJECT")
    region: str = Field(default="us-central1", validation_alias="GOOGLE_CLOUD_REGION")

    # Vertex serves models from a *location*, which is not the same thing as the
    # region infrastructure lives in — and getting this wrong is a compliance
    # failure, not a latency problem. Regional endpoints such as us-central1 only
    # serve up to Gemini 2.5; every 3.x model returns 404 there and is available
    # only from `global`. Since the hackathon mandates Gemini 3.5 or newer, a
    # regional endpoint would quietly force a non-compliant model.
    #
    # Cloud Run and Firestore still live in `region`; only model serving uses this.
    vertex_location: str = Field(default="global", validation_alias="GOOGLE_CLOUD_LOCATION")

    # Verified with `make models` against the live API. Two things to keep true:
    #   - both must be Gemini 3.5 or newer, or the entry fails the mandatory check
    #   - gemini-3.5-pro does NOT exist. It was the obvious guess and it was wrong;
    #     the newest explicit model is the deep tier instead, because no pro-class
    #     model at 3.5+ is available on either backend.
    # Defaults matter here: the deployed service falls back to them whenever an
    # env var is missing, which is how a non-existent model reached production
    # and only surfaced on /health.
    model_fast: str = Field(default="gemini-3.5-flash", validation_alias="VIGIL_MODEL_FAST")
    model_deep: str = Field(default="gemini-3.6-flash", validation_alias="VIGIL_MODEL_DEEP")
    api_key: str = Field(default="", validation_alias="GOOGLE_API_KEY")

    # Layer 1 of the runaway-agent defence: exceeding any of these aborts the run
    # and writes an audit entry rather than silently continuing. Layer 2 is Cloud
    # Run --max-instances, layer 3 is billing budget alerts.
    max_steps: int = Field(default=25, validation_alias="VIGIL_MAX_STEPS")
    max_tool_calls: int = Field(default=40, validation_alias="VIGIL_MAX_TOOL_CALLS")
    max_tokens_per_run: int = Field(default=200_000, validation_alias="VIGIL_MAX_TOKENS_PER_RUN")

    topic_events: str = Field(default="vigil.events.clean", validation_alias="VIGIL_TOPIC_EVENTS")
    topic_dlq: str = Field(default="vigil.events.dead", validation_alias="VIGIL_TOPIC_DLQ")
    subscription_worker: str = Field(
        default="vigil.worker", validation_alias="VIGIL_SUBSCRIPTION_WORKER"
    )
    bucket_raw: str = Field(default="vigil-raw", validation_alias="VIGIL_BUCKET_RAW")

    api_auth_key: str = Field(default="dev-local-key-change-me", validation_alias="VIGIL_API_KEY")

    # ── Emulator awareness: read the same variables the Google SDKs read ──────
    @property
    def firestore_emulator(self) -> str | None:
        return os.environ.get("FIRESTORE_EMULATOR_HOST")

    @property
    def pubsub_emulator(self) -> str | None:
        return os.environ.get("PUBSUB_EMULATOR_HOST")

    @property
    def storage_emulator(self) -> str | None:
        return os.environ.get("STORAGE_EMULATOR_HOST")

    @property
    def uses_emulators(self) -> bool:
        return bool(self.firestore_emulator or self.pubsub_emulator)

    @property
    def model_enabled(self) -> bool:
        """False when no credentials are configured, so the skeleton still runs
        end-to-end offline — the worker logs a skip instead of crashing."""
        use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
        return bool(self.api_key) or use_vertex in {"1", "true", "yes"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
