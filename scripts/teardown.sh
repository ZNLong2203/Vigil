#!/usr/bin/env bash
#
# Run this the moment filming is finished.
#
# The rules are explicit that the app does not need to stay live for judging —
# only that there is clear proof it ran on Google Cloud. So we scale the service
# to nothing and stop every recurring trigger, while leaving the deployment (and
# therefore the console evidence) intact.
#
#   ./scripts/teardown.sh          scale to zero, keep evidence
#   ./scripts/teardown.sh --purge  delete the service and subscription too
#
set -euo pipefail

REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
SERVICE="${VIGIL_SERVICE:-vigil}"
SUBSCRIPTION="${VIGIL_SUBSCRIPTION_WORKER:-vigil.worker}"
PURGE="${1:-}"

PROJECT="$(gcloud config get-value project 2>/dev/null)"
echo "project: $PROJECT"

echo "→ pausing scheduler jobs"
for job in $(gcloud scheduler jobs list --location="$REGION" --format='value(name)' 2>/dev/null); do
  gcloud scheduler jobs pause "$job" --location="$REGION" --quiet || true
done

if [[ "$PURGE" == "--purge" ]]; then
  echo "→ deleting push subscription"
  gcloud pubsub subscriptions delete "$SUBSCRIPTION" --quiet || true
  echo "→ deleting Cloud Run service"
  gcloud run services delete "$SERVICE" --region="$REGION" --quiet || true
  echo "Purged. Console history remains as evidence; redeploy with ./deploy.sh"
else
  echo "→ capping Cloud Run at zero instances"
  gcloud run services update "$SERVICE" --region="$REGION" \
    --min-instances=0 --max-instances=1 --quiet
  echo "Service still exists (evidence intact) but sleeps when idle."
fi

echo
echo "Remaining cost after this: effectively zero."
echo "Full cleanup when the judging period ends (Oct 1, 2026):"
echo "  gcloud projects delete $PROJECT"
