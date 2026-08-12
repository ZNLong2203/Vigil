#!/usr/bin/env bash
#
# The exactly-once proof, on camera.
#
#   make up && make api      # in another terminal
#   make chaos
#
# What it does:
#   1. starts a worker that holds each claim open for 15 seconds
#   2. publishes one event
#   3. SIGKILLs the worker while the claim is held — the crash happens in the
#      exact window between "I have claimed this step" and "I have done it"
#   4. restarts the worker, which redelivers the same message
#   5. counts what ended up in Firestore
#
# The run must show exactly one idempotency claim and one checkpoint. A system
# without ADR 002 shows two, and in this domain that is a benefits claim filed
# twice.
#
set -euo pipefail
cd "$(dirname "$0")/.."

API="${VIGIL_API:-http://localhost:8000}"
KEY="${VIGIL_API_KEY:-dev-local-key-change-me}"
LOG=".data/chaos-worker.log"
mkdir -p .data

[[ -n "${FIRESTORE_EMULATOR_HOST:-}" ]] || export FIRESTORE_EMULATOR_HOST=localhost:8080
[[ -n "${PUBSUB_EMULATOR_HOST:-}" ]] || export PUBSUB_EMULATOR_HOST=localhost:8085

curl -sf "$API/health" >/dev/null || { echo "✗ API not reachable at $API — run 'make api'"; exit 1; }

cleanup() { [[ -n "${WORKER_PID:-}" ]] && kill -9 "$WORKER_PID" 2>/dev/null || true; }
trap cleanup EXIT

echo "── 1. worker up, holding each claim for 15s ──────────────────────────────"
VIGIL_DEMO_DELAY_MS=15000 uv run python -m vigil.worker >"$LOG" 2>&1 &
WORKER_PID=$!
sleep 6

echo "── 2. publishing one event ──────────────────────────────────────────────"
run_id=$(curl -sS -X POST "$API/events" \
  -H 'Content-Type: application/json' -H "X-API-Key: $KEY" \
  -d '{"kind":"document","subject":"care-subject-001",
       "source_uri":"gs://vigil-raw/synthetic/benefits-letter.pdf",
       "body":{"scenario":"chaos"}}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])')
echo "   run_id: $run_id"

echo "── 3. waiting for the claim, then SIGKILL ───────────────────────────────"
for _ in $(seq 1 20); do
  grep -q 'demo.delay' "$LOG" && break
  sleep 0.5
done
grep -q 'demo.delay' "$LOG" || { echo "✗ worker never picked the message up"; cat "$LOG"; exit 1; }
echo "   claim is held — killing PID $WORKER_PID"
kill -9 "$WORKER_PID"; wait "$WORKER_PID" 2>/dev/null || true
echo "   worker dead mid-step. The claim survives in Firestore."

echo "── 4. restarting the worker (message will be redelivered) ───────────────"
uv run python -m vigil.worker >>"$LOG" 2>&1 &
WORKER_PID=$!
sleep 40

echo "── 5. counting what actually happened ───────────────────────────────────"
uv run python - "$run_id" <<'PY'
import sys
sys.path.insert(0, "src")
from vigil.state import db

run_id = sys.argv[1]
claims = [d.to_dict() for d in db().collection("idempotency").where("run_id", "==", run_id).stream()]
checkpoints = [
    d.to_dict() for d in db().collection("runs").document(run_id).collection("checkpoints").stream()
]
run = (db().collection("runs").document(run_id).get().to_dict() or {})

print(f"   idempotency claims : {len(claims)}   {[c.get('status') for c in claims]}")
print(f"   checkpoints        : {len(checkpoints)}   {[c.get('status') for c in checkpoints]}")
print(f"   run status         : {run.get('status')}")
print()
if len(claims) == 1 and len(checkpoints) == 1 and run.get("status") == "done":
    print("   ✓ EXACTLY ONCE — the crash cost nothing and duplicated nothing.")
    raise SystemExit(0)
print("   ✗ Not exactly-once. Investigate before filming.")
raise SystemExit(1)
PY

echo
echo "Duplicate-suppression evidence in the log:"
grep -E 'step.skipped.duplicate|step.duplicate_suppressed' "$LOG" | tail -3 || echo "   (none — the kill landed before the claim)"
