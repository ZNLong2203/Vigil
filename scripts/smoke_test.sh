#!/usr/bin/env bash
# One event, end to end: API -> Pub/Sub -> worker -> Firestore.
# Exits non-zero if the run never reaches a terminal state.
set -euo pipefail

API="${VIGIL_API:-http://localhost:8000}"
KEY="${VIGIL_API_KEY:-dev-local-key-change-me}"

echo "→ POST $API/events"
response=$(curl -sS -X POST "$API/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{
        "kind": "document",
        "subject": "care-subject-001",
        "source_uri": "gs://vigil-raw/synthetic/lab-result-01.pdf",
        "body": {"note": "smoke test — synthetic data only"}
      }')

echo "$response"
run_id=$(printf '%s' "$response" | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
echo "→ run_id: $run_id"

echo "→ waiting for the worker to finish the run…"
for _ in $(seq 1 30); do
  status=$(cd "$(dirname "$0")/.." && uv run python - "$run_id" <<'PY' 2>/dev/null || true
import sys
sys.path.insert(0, "src")
from vigil.state import db
doc = db().collection("runs").document(sys.argv[1]).get()
print((doc.to_dict() or {}).get("status", "missing"))
PY
)
  if [[ "$status" == "done" ]]; then
    echo "✓ run completed — check the trace at http://localhost:16686"
    exit 0
  fi
  sleep 1
done

echo "✗ run did not complete. Is 'make worker' running?" >&2
exit 1
