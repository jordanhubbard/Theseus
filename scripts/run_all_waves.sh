#!/usr/bin/env bash
# run_all_waves.sh — Run all pending synthesis waves, committing every N waves.
# Usage: bash scripts/run_all_waves.sh [--commit-every N] [--jobs J]
# Writes progress to logs/wave_runner.log

set -euo pipefail
cd "$(dirname "$0")/.."

COMMIT_EVERY=${COMMIT_EVERY:-5}
JOBS=${JOBS:-4}
LLM_TIMEOUT=${LLM_TIMEOUT:-180}   # seconds per LLM call; prevents runaway stalls
LOGFILE="logs/wave_runner.log"
LOCKFILE="logs/wave_runner.lock"
mkdir -p logs

# Singleton guard — exit if another instance is already running
if [ -f "$LOCKFILE" ]; then
    other_pid=$(cat "$LOCKFILE" 2>/dev/null)
    if kill -0 "$other_pid" 2>/dev/null; then
        echo "Runner already running (PID $other_pid). Exiting." >&2
        exit 0
    fi
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

log() { echo "[$(date '+%H:%M:%S')] $*" >> "$LOGFILE"; echo "[$(date '+%H:%M:%S')] $*" >&2; }

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --commit-every) COMMIT_EVERY="$2"; shift 2 ;;
        --jobs)         JOBS="$2";         shift 2 ;;
        *)              echo "Unknown arg: $1"; exit 1 ;;
    esac
done

log "=== Wave runner start (commit every $COMMIT_EVERY waves, $JOBS jobs) ==="

count=0
batch_count=0

while true; do
    # Get next wave needing work: pending waves first, then partial waves
    # that still have unrun specs (Specs < total, meaning some never ran).
    # This avoids infinite retry loops on consistently-failing specs.
    wave=$(python3 tools/synthesize_waves.py --list 2>/dev/null \
        | awk '$6 == "pending" {print $1; exit}')
    if [[ -z "$wave" ]]; then
        # No pure-pending waves; look for partial waves with un-run specs
        wave=$(python3 tools/synthesize_waves.py --list 2>/dev/null \
            | awk '$6 == "partial" && $3 < $2 {print $1; exit}')
    fi

    if [[ -z "$wave" ]]; then
        log "No more waves needing work — all done!"
        break
    fi

    log "Running wave $wave ..."
    if python3 tools/synthesize_waves.py --wave "$wave" --jobs "$JOBS" --timeout "$LLM_TIMEOUT" \
            >> "$LOGFILE" 2>&1; then
        log "  Wave $wave: DONE"
    else
        log "  Wave $wave: exited non-zero (check log for details)"
    fi

    count=$((count + 1))
    batch_count=$((batch_count + 1))

    if [[ $batch_count -ge $COMMIT_EVERY ]]; then
        log "Committing after $batch_count waves ..."
        git add zspecs/ reports/synthesis/wave_state.json 2>/dev/null || true
        if ! git diff --cached --quiet; then
            git commit -m "feat: synthesize waves batch (auto-commit after $COMMIT_EVERY waves)

Waves completed in this batch ended with: $wave
Total waves run so far in this session: $count

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>" \
                >> "$LOGFILE" 2>&1
            git push >> "$LOGFILE" 2>&1
            log "  Committed and pushed."
        else
            log "  Nothing to commit."
        fi
        batch_count=0
    fi
done

# Final commit for any remainder
git add zspecs/ reports/synthesis/wave_state.json 2>/dev/null || true
if ! git diff --cached --quiet; then
    git commit -m "feat: synthesize waves — final batch commit

Total waves run in this session: $count

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>" \
        >> "$LOGFILE" 2>&1
    git push >> "$LOGFILE" 2>&1
    log "Final commit pushed."
fi

log "=== Wave runner complete. Total waves run: $count ==="
