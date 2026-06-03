"""Send job search pipeline results to Discord."""
import sys
from pathlib import Path
from datetime import datetime
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def send_discord_start():
    """Notify Discord when pipeline starts."""
    message = f"""🔍 **Job Search Pipeline Running**

**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} PT
**Status:** In progress (discovery/scoring phase)
**Config:** 7 searches across LinkedIn + Indeed for Vancouver BC + remote

**Will report back when complete with:**
- Jobs discovered
- Jobs scored (GLM-4.7)
- Jobs passing threshold (≥7.5/10)
- Written to Obsidian inbox for review

_Hank (Hermes Agent)_"""

    try:
        from hermes_tools import send_message
        send_message(action="send", message=message, target="discord:#jobs")
        return True
    except Exception as e:
        print(f"[!] Discord start notification failed: {e}")
        return False


def send_discord_summary(results: dict, duration_minutes: float = 0):
    """Send pipeline completion summary to Discord #jobs channel."""
    message = f"""✅ **Job Search Pipeline Complete**

**Duration:** ~{int(duration_minutes)} minutes
**Jobs Discovered:** {results.get('discovered', 0)}
**Jobs Scored:** {results.get('scored', 0)}
**Jobs Passing Threshold:** {results.get('passed', 0)}
**Deduped:** {results.get('deduped', 0)} | **Pre-filtered:** {results.get('filtered_title', 0) + results.get('filtered_location', 0)}

**Top 5 Matches:**
{chr(10).join([f"• {j.get('title')} at {j.get('company')} — {j.get('score', {}).get('weighted_total', 0)}/10" for j in results.get('top_jobs', [])[:5]])}

**Errors:** {len(results.get('errors', []))}

_Jobs written to inbox: `00-Inbox/` → routed to `06-Career/Jobs/[Company]/[Role]/`_
_Daily digest: `01-Daily/{datetime.now().strftime('%Y-%m-%d')}.md`_

_Hank (Hermes Agent)_"""

    try:
        from hermes_tools import send_message
        send_message(action="send", message=message, target="discord:#jobs")
        return True
    except Exception as e:
        print(f"[!] Discord summary notification failed: {e}")
        print(f"[!] Summary written to /tmp/jobsearch_summary.txt")
        with open("/tmp/jobsearch_summary.txt", "w") as f:
            f.write(message)
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovered", type=int, default=0)
    parser.add_argument("--scored", type=int, default=0)
    parser.add_argument("--passed", type=int, default=0)
    parser.add_argument("--cover-letters", type=int, default=0)
    parser.add_argument("--duration", type=float, default=0)
    args = parser.parse_args()

    sample_results = {
        "discovered": args.discovered,
        "scored": args.scored,
        "passed": args.passed,
        "cover_letters": args.cover_letters,
        "top_jobs": [],
        "errors": []
    }
    send_discord_summary(sample_results, args.duration)
