#!/bin/bash
# Daily job search pipeline wrapper
# Run by Hermes cron at 06:00 PT daily

set -euo pipefail

PROJECT_DIR="/opt/data/seth-jobsearch-auto"
export PYTHONPATH="/opt/data/.pylibs:src"

cd "$PROJECT_DIR"

# Load API keys
set -a; source "$PROJECT_DIR/.env" 2>/dev/null; set +a

# Run pipeline: discover -> dedup -> pre-filter -> score -> write to vault
# --score-only: skip cover letters (handled separately)
python3 -m src.main --score-only --verbose 2>&1

# Rebuild kanban board from current vault state
python3 src/rebuild_kanban.py 2>&1
