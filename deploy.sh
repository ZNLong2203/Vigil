#!/usr/bin/env bash
#
# One-command deploy to Google Cloud. Idempotent — safe to re-run.
#
#   ./deploy.sh
#
# Requires: gcloud, an authenticated account, and a project with billing enabled.
#   gcloud auth login
#   gcloud config set project YOUR_PROJECT_ID
#
# Cost posture (see README §Cost control):
#   min-instances=0   the service sleeps when idle and costs nothing
#   max-instances=3   caps the blast radius of a runaway loop
#   push subscription instead of a polling worker, so nothing stays warm
#
set -euo pipefail

REGION="${GOOGLE_CLOUD_REGION:-us-central1}"

# Where Vertex serves models from, which is NOT where the infrastructure lives.
# Regional endpoints only serve up to Gemini 2.5; every 3.x model returns 404
# there. The hackathon mandates Gemini 3.5 or newer, so this has to reach the
# container — the SDK reads GOOGLE_CLOUD_LOCATION from the environment when it
# builds its client, and a service missing it fails at the first model call
# rather than at deploy time.
VERTEX_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"

# Model ids travel with the deployment. Leaving them to the container's defaults
# means local and cloud can silently disagree — which is exactly what happened:
# a stale default put a non-existent model in production, and nothing failed
# until /health printed it back. Verify with `make models` before deploying.
MODEL_FAST="${VIGIL_MODEL_FAST:-gemini-3.5-flash}"
MODEL_DEEP="${VIGIL_MODEL_DEEP:-gemini-3.6-flash}"

# How long Pub/Sub waits for the push endpoint before assuming the delivery was
# lost and sending it again.
#
# The default 60s is far shorter than a fleet run: three agent hops at 10-30
# seconds each, plus tool calls, is minutes. At 60s every run was redelivered
# mid-flight. Nothing was done twice — the per-step idempotency claims held —
# but the duplicate work was pure waste, and each redelivery is a second
# container instance spun up to discover it has nothing to do.
#
# 600s is the maximum Pub/Sub allows, and still shorter than the Cloud Run
# request timeout (900s), so the request is never cut off mid-run.
ACK_DEADLINE="${VIGIL_ACK_DEADLINE:-600}"

# Gemma redacts names before anything reaches the reasoning tier (ADR 005). It is
# served by the Gemini API, not Vertex, so it carries its own credential — read
# from .env if present. Optional: without it the trust boundary falls back to the
# regex tier, which finds structured identifiers and cannot find a person's name.
# The fallback logs a warning saying exactly that rather than degrading quietly.
GEMMA_KEY="${VIGIL_GEMMA_API_KEY:-$(grep -sh '^VIGIL_GEMMA_API_KEY=' .env | cut -d= -f2- | tr -d '\r')}"
GEMMA_MODEL="${VIGIL_MODEL_GEMMA:-gemma-4-31b-it}"
SERVICE="${VIGIL_SERVICE:-vigil}"
TOPIC_EVENTS="${VIGIL_TOPIC_EVENTS:-vigil.events.clean}"
TOPIC_DLQ="${VIGIL_TOPIC_DLQ:-vigil.events.dead}"
SUBSCRIPTION="${VIGIL_SUBSCRIPTION_WORKER:-vigil.worker}"
SA_RUN="vigil-run"
SA_PUSH="vigil-push"

bold() { printf "\n\033[1m%s\033[0m\n" "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

have gcloud || { echo "gcloud not found — https://cloud.google.com/sdk/docs/install"; exit 1; }

PROJECT="$(gcloud config get-value project 2>/dev/null)"
[[ -n "$PROJECT" && "$PROJECT" != "(unset)" ]] || {
  echo "No project set. Run: gcloud config set project YOUR_PROJECT_ID"; exit 1; }

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
bold "Project $PROJECT ($PROJECT_NUMBER) · region $REGION"

# ── 1. APIs ──────────────────────────────────────────────────────────────────
bold "1/7  Enabling APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudtrace.googleapis.com \
  storage.googleapis.com \
  --quiet

# ── 2. Firestore ─────────────────────────────────────────────────────────────
bold "2/7  Firestore (native mode)"
if gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  echo "    already exists"
else
  gcloud firestore databases create --location="$REGION" --type=firestore-native --quiet
fi

# ── 3. Pub/Sub ───────────────────────────────────────────────────────────────
bold "3/7  Pub/Sub topics and the artifact bucket"
for t in "$TOPIC_EVENTS" "$TOPIC_DLQ"; do
  gcloud pubsub topics describe "$t" >/dev/null 2>&1 \
    && echo "    topic $t already exists" \
    || gcloud pubsub topics create "$t" --quiet
done

# ── 3b. Raw artifact bucket ──────────────────────────────────────────────────
#
# Uniform bucket-level access, no public reads: uploads are photographs of
# medication and paperwork. Synthetic here, but the access model has to be the
# one the real thing would need, or the demo is teaching the wrong lesson.
#
# A 30-day lifecycle rule keeps the footprint near zero — the hackathon's own
# cost guidance — and means nothing lingers after judging.
BUCKET="${VIGIL_BUCKET_RAW:-${PROJECT}-vigil-raw}"
if gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  echo "    bucket ${BUCKET} already exists"
else
  gcloud storage buckets create "gs://${BUCKET}" \
    --location="$REGION" --uniform-bucket-level-access --quiet
fi
printf '{"rule":[{"action":{"type":"Delete"},"condition":{"age":30}}]}' >/tmp/vigil-lifecycle.json
gcloud storage buckets update "gs://${BUCKET}" \
  --lifecycle-file=/tmp/vigil-lifecycle.json --quiet >/dev/null

# ── 4. Service accounts (one identity per role — least privilege) ────────────
bold "4/7  Service accounts"
create_sa() {
  local name="$1" display="$2"
  gcloud iam service-accounts describe "${name}@${PROJECT}.iam.gserviceaccount.com" >/dev/null 2>&1 \
    && echo "    ${name} already exists" \
    || gcloud iam service-accounts create "$name" --display-name="$display" --quiet
}
create_sa "$SA_RUN"  "Vigil Cloud Run runtime"
create_sa "$SA_PUSH" "Vigil Pub/Sub push identity"

RUN_SA="${SA_RUN}@${PROJECT}.iam.gserviceaccount.com"
PUSH_SA="${SA_PUSH}@${PROJECT}.iam.gserviceaccount.com"

for role in roles/datastore.user roles/pubsub.publisher roles/aiplatform.user \
            roles/storage.objectAdmin roles/cloudtrace.agent \
            roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${RUN_SA}" --role="$role" \
    --condition=None --quiet >/dev/null
done
echo "    roles bound to ${SA_RUN}"

# ── 5. Cloud Run ─────────────────────────────────────────────────────────────
bold "5/7  Deploying Cloud Run service '${SERVICE}'"
API_KEY="${VIGIL_API_KEY:-}"
[[ -n "$API_KEY" ]] || API_KEY="$(python3 -c 'import secrets;print(secrets.token_urlsafe(32))')"

# The UI is a static bundle, so anything given to it at build time is readable by
# anyone who opens the page. Baking the API key in makes the hosted demo work
# end-to-end for a judge with one click — and makes that key public. Both are
# true, so neither is hidden:
#
#   - it is a throttle against stray internet traffic and crawlers, which is all
#     it ever was (see require_api_key). It is not an access control here.
#   - the real cost ceiling is elsewhere and does not depend on secrecy:
#     --max-instances=3, the per-run token budget, and billing budget alerts.
#   - rotate it after filming, and run scripts/teardown.sh. The rules do not
#     require the app to stay live for judging.
#
# Set VIGIL_PUBLIC_UI=0 to build the UI without a key: it then opens in fixture
# mode, showing the same story from committed data with nothing live behind it.
if [[ "${VIGIL_PUBLIC_UI:-1}" == "1" ]]; then
  UI_BUILD_ARGS="NEXT_PUBLIC_VIGIL_API=,NEXT_PUBLIC_VIGIL_KEY=${API_KEY}"
else
  UI_BUILD_ARGS="NEXT_PUBLIC_VIGIL_API=,NEXT_PUBLIC_VIGIL_KEY="
fi

gcloud run deploy "$SERVICE" \
  --source=. \
  --set-build-env-vars="$UI_BUILD_ARGS" \
  --region="$REGION" \
  --service-account="$RUN_SA" \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --cpu=1 --memory=512Mi \
  --concurrency=10 \
  --timeout=900 \
  --set-env-vars="VIGIL_ENV=cloud,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_REGION=${REGION},GOOGLE_CLOUD_LOCATION=${VERTEX_LOCATION},GOOGLE_GENAI_USE_VERTEXAI=true,VIGIL_MODEL_FAST=${MODEL_FAST},VIGIL_MODEL_DEEP=${MODEL_DEEP},VIGIL_API_KEY=${API_KEY},VIGIL_TOPIC_EVENTS=${TOPIC_EVENTS},VIGIL_TOPIC_DLQ=${TOPIC_DLQ},VIGIL_SUBSCRIPTION_WORKER=${SUBSCRIPTION},VIGIL_BUCKET_RAW=${BUCKET},VIGIL_MODEL_GEMMA=${GEMMA_MODEL},VIGIL_GEMMA_API_KEY=${GEMMA_KEY}" \
  --quiet

URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"

# ── 6. Push subscription (no polling worker => nothing stays warm) ───────────
bold "6/7  Pub/Sub push subscription"
gcloud run services add-iam-policy-binding "$SERVICE" \
  --region="$REGION" --member="serviceAccount:${PUSH_SA}" \
  --role=roles/run.invoker --quiet >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role=roles/iam.serviceAccountTokenCreator --condition=None --quiet >/dev/null

if gcloud pubsub subscriptions describe "$SUBSCRIPTION" >/dev/null 2>&1; then
  # Converge every setting, not just the endpoint. An idempotent script that
  # only fixes resources it creates is not idempotent — the ack deadline was
  # wrong on an existing subscription for exactly this reason, and re-running
  # the deploy silently left it wrong.
  gcloud pubsub subscriptions update "$SUBSCRIPTION" \
    --push-endpoint="${URL}/pubsub/push" \
    --push-auth-service-account="$PUSH_SA" \
    --ack-deadline="$ACK_DEADLINE" \
    --dead-letter-topic="$TOPIC_DLQ" \
    --max-delivery-attempts=5 --quiet
else
  gcloud pubsub subscriptions create "$SUBSCRIPTION" \
    --topic="$TOPIC_EVENTS" \
    --push-endpoint="${URL}/pubsub/push" \
    --push-auth-service-account="$PUSH_SA" \
    --dead-letter-topic="$TOPIC_DLQ" \
    --max-delivery-attempts=5 \
    --ack-deadline="$ACK_DEADLINE" --quiet
fi

# ── 7. Weekly digest schedule ────────────────────────────────────────────────
#
# The one genuinely periodic thing in the system. Everything else reacts to an
# event; a weekly note is a weekly note, and one that has to be requested is one
# nobody reads.
#
# Video is off on the scheduled run: it costs minutes and Cloud Scheduler's
# deadline is measured in seconds. The text and the urgency cue — the parts a
# caregiver acts on — are fast. Request the video explicitly when it is wanted.
bold "7/7  Weekly digest schedule"
SCHEDULE_JOB="${VIGIL_SCHEDULE_JOB:-vigil-weekly-digest}"
SCHEDULE_CRON="${VIGIL_SCHEDULE_CRON:-0 8 * * 1}"

if gcloud scheduler jobs describe "$SCHEDULE_JOB" --location="$REGION" >/dev/null 2>&1; then
  # `update http` takes --update-headers; only `create` accepts --headers.
  # Re-running the deploy failed on this, which is the one thing an idempotent
  # script must not do.
  gcloud scheduler jobs update http "$SCHEDULE_JOB" --location="$REGION" \
    --schedule="$SCHEDULE_CRON" \
    --uri="${URL}/digest" \
    --http-method=POST \
    --update-headers="Content-Type=application/json,X-API-Key=${API_KEY}" \
    --message-body='{"subject":"care-subject-001","days":7,"with_video":false}' \
    --attempt-deadline=180s --quiet
else
  gcloud scheduler jobs create http "$SCHEDULE_JOB" --location="$REGION" \
    --schedule="$SCHEDULE_CRON" \
    --time-zone="Etc/UTC" \
    --uri="${URL}/digest" \
    --http-method=POST \
    --headers="Content-Type=application/json,X-API-Key=${API_KEY}" \
    --message-body='{"subject":"care-subject-001","days":7,"with_video":false}' \
    --attempt-deadline=180s --quiet
fi
echo "    ${SCHEDULE_JOB}: ${SCHEDULE_CRON} (Mondays 08:00 UTC)"

bold "Deployed"
cat <<EOF
  URL        ${URL}
  API key    ${API_KEY}
  health     curl ${URL}/health
  send event curl -X POST ${URL}/events \\
               -H 'Content-Type: application/json' \\
               -H 'X-API-Key: ${API_KEY}' \\
               -d '{"kind":"document","subject":"care-subject-001","body":{}}'

  Proof to capture for the demo video:
    Cloud Run   https://console.cloud.google.com/run/detail/${REGION}/${SERVICE}/metrics?project=${PROJECT}
    Logs        https://console.cloud.google.com/run/detail/${REGION}/${SERVICE}/logs?project=${PROJECT}
    Traces      https://console.cloud.google.com/traces/list?project=${PROJECT}
    Firestore   https://console.cloud.google.com/firestore/databases/-default-/data?project=${PROJECT}

  Weekly digest  ${SCHEDULE_JOB} — runs Mondays 08:00 UTC
  Test it now    gcloud scheduler jobs run ${SCHEDULE_JOB} --location=${REGION}

  When you are done filming:  ./scripts/teardown.sh
EOF
