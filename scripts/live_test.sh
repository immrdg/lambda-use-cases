#!/usr/bin/env bash
# live_test.sh — End-to-end test for s3-cleanup Lambda
# Usage: ./scripts/live_test.sh
#
# What it does:
#   1. Uploads test files to S3
#   2. Sets RETENTION_DAYS=0 and reschedules EventBridge to fire in ~2 mins
#   3. Waits and tails CloudWatch logs until deletions appear
#   4. Restores original config

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
PROFILE="immrdg21"
REGION="us-east-1"
BUCKET="s3-cleanup-bucket-dev-use-case-1"
FUNCTION="s3-cleanup-dev"
EB_RULE="s3-cleanup-dev-schedule"
LOG_GROUP="/aws/lambda/${FUNCTION}"

ORIGINAL_RETENTION=30
ORIGINAL_SCHEDULE="rate(1 day)"
TEST_SCHEDULE="rate(1 minute)"   # fire every minute so we don't wait long
WAIT_MINUTES=3                   # wait this many minutes before checking logs

# ── Helpers ───────────────────────────────────────────────────────────────────
aws_cmd() { aws "$@" --profile "$PROFILE" --region "$REGION"; }

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Cleanup trap — always restore on exit ─────────────────────────────────────
restore() {
  log "Restoring original config..."
  aws_cmd lambda update-function-configuration \
    --function-name "$FUNCTION" \
    --environment "Variables={BUCKET_NAME=${BUCKET},RETENTION_DAYS=${ORIGINAL_RETENTION}}" \
    --query 'FunctionName' --output text > /dev/null

  aws_cmd events put-rule \
    --name "$EB_RULE" \
    --schedule-expression "$ORIGINAL_SCHEDULE" \
    --state ENABLED \
    --query 'RuleArn' --output text > /dev/null

  log "Restored: RETENTION_DAYS=${ORIGINAL_RETENTION}, schedule='${ORIGINAL_SCHEDULE}'"
}
trap restore EXIT

# ── Step 1: Upload test files ─────────────────────────────────────────────────
log "Uploading test files to s3://${BUCKET}/ ..."
for i in $(seq 1 5); do
  KEY="test-file-${i}.txt"
  echo "Test content ${i} — uploaded at $(date -u)" | \
    aws_cmd s3 cp - "s3://${BUCKET}/${KEY}"
  log "  Uploaded ${KEY}"
done

log "Current bucket contents:"
aws_cmd s3 ls "s3://${BUCKET}/" | awk '{print "  " $0}'

# ── Step 2: Adjust Lambda — RETENTION_DAYS=0 ─────────────────────────────────
log "Setting RETENTION_DAYS=0 on Lambda..."
aws_cmd lambda update-function-configuration \
  --function-name "$FUNCTION" \
  --environment "Variables={BUCKET_NAME=${BUCKET},RETENTION_DAYS=0}" \
  --query 'FunctionName' --output text > /dev/null

# Wait for update to propagate
aws_cmd lambda wait function-updated --function-name "$FUNCTION"
log "Lambda config updated."

# ── Step 3: Reschedule EventBridge to every 1 minute ─────────────────────────
log "Rescheduling EventBridge rule to '${TEST_SCHEDULE}'..."
aws_cmd events put-rule \
  --name "$EB_RULE" \
  --schedule-expression "$TEST_SCHEDULE" \
  --state ENABLED \
  --query 'RuleArn' --output text > /dev/null
log "EventBridge rule updated."

# ── Step 4: Watch bucket and logs ────────────────────────────────────────────
log "Waiting ${WAIT_MINUTES} minutes for EventBridge to trigger Lambda..."
log "Tailing CloudWatch logs (Ctrl+C to stop early, config will still restore):"
echo ""

END_TIME=$(( $(date +%s) + WAIT_MINUTES * 60 ))

# Tail logs in background, kill it when done
aws_cmd logs tail "$LOG_GROUP" --follow &
TAIL_PID=$!

while [ "$(date +%s)" -lt "$END_TIME" ]; do
  sleep 10
  REMAINING=$(( (END_TIME - $(date +%s)) / 60 + 1 ))
  log "  ~${REMAINING} min remaining..."
done

kill "$TAIL_PID" 2>/dev/null || true
echo ""

# ── Step 5: Show final bucket state ──────────────────────────────────────────
log "Final bucket contents (should be empty):"
CONTENTS=$(aws_cmd s3 ls "s3://${BUCKET}/")
if [ -z "$CONTENTS" ]; then
  log "  ✓ Bucket is empty — deletions confirmed!"
else
  log "  Objects still present:"
  echo "$CONTENTS" | awk '{print "  " $0}'
fi

log "Done. Restoring config on exit..."
# trap will fire here
