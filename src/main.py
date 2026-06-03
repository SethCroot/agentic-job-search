#!/usr/bin/env python3
"""Seth JobSearch Auto - CLI entry point."""
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import time

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Ensure .env is loaded
from dotenv import load_dotenv
load_dotenv()

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.engine import PipelineEngine
from src.config import Config
from src.discord_notifier import send_discord_start, send_discord_summary


def main():
    parser = argparse.ArgumentParser(description="Seth JobSearch Auto")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to vault or calling AI")
    parser.add_argument("--discover-only", action="store_true", help="Only discover jobs, no scoring/tailoring")
    parser.add_argument("--score-only", action="store_true", help="Score discovered jobs, no tailoring")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of jobs to process")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-discord", action="store_true", help="Skip Discord notifications")
    args = parser.parse_args()

    config = Config()

    if args.verbose:
        print(f"AI: {config.ai.get('provider')} / {config.ai.get('model')}")
        print(f"Vault: {config.vault_path}")
        print(f"Employers: {config.get_employer_names()}")
        print(f"Searches: {len(config.searches.get('searches', []))}")
        print()

    # Notify Discord start (unless suppressed)
    if not args.no_discord:
        send_discord_start()

    # Track timing
    start_time = time.time()

    engine = PipelineEngine(config=config, dry_run=args.dry_run)
    results = engine.run(discover_only=args.discover_only, score_only=args.score_only, limit=args.limit)

    duration_minutes = (time.time() - start_time) / 60

    print(f"\n{'='*50}")
    print(f"RESULTS")
    print(f"{'='*50}")
    print(f"Discovered:  {results['discovered']}")
    print(f"Deduped:     {results.get('deduped', 0)} (already in vault)")
    print(f"Pre-filter:  {results.get('filtered_title', 0)} title + {results.get('filtered_location', 0)} location")
    print(f"Scored:      {results['scored']} (by LLM)")
    print(f"Passed:      {results['passed']}")
    print(f"Materials:   {results['cover_letters']}")
    print(f"Duration:    {duration_minutes:.1f} minutes")

    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for err in results['errors'][:5]:
            print(f"  - {err}")

    # Notify Discord complete (unless suppressed)
    if not args.no_discord:
        send_discord_summary(results, duration_minutes)

    return 0 if not results['errors'] else 1


if __name__ == "__main__":
    sys.exit(main())