#!/usr/bin/env bash
# Seth JobSearch Auto — Daily Pipeline Runner
# Called by Hermes cron job system at 08:00 AEST
# Usage: bash run-pipeline.sh [--discover-only] [--limit N]

set -euo pipefail

PROJECT_DIR="/home/seth/.openclaw/workspace/seth-jobsearch-auto"
LOG_FILE="/tmp/jobsearch-pipeline-$(date +%Y%m%d-%H%M%S).log"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S AEST')"

echo "[$TIMESTAMP] JobSearch Auto pipeline starting..." | tee "$LOG_FILE"
echo "[$TIMESTAMP] Project dir: $PROJECT_DIR" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR"

# Activate virtual environment
source .venv/bin/activate

# Load environment variables
set -a
source .env
set +a

# Run the pipeline
echo "[$(date '+%H:%M:%S')] Running pipeline..." | tee -a "$LOG_FILE"
python -u src/main.py --no-discord "$@" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

DURATION=$(tail -1 "$LOG_FILE" 2>/dev/null || echo "unknown")
echo "[$(date '+%H:%M:%S')] Pipeline exited with code $EXIT_CODE" | tee -a "$LOG_FILE"

exit $EXIT_CODE
