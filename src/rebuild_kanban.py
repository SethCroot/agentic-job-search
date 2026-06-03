#!/usr/bin/env python3
"""Rebuild the Kanban board from vault job files.

Scans /vault/06-Career/Jobs/ for job.md files, reads their frontmatter,
and rebuilds the Kanban board grouped by status.

Usage:
    python3 rebuild_kanban.py [--kanban PATH] [--jobs-dir PATH]
"""
import argparse
import re
from pathlib import Path


KANBAN_DEFAULT = Path("/vault/02-Projects/Seth JobSearch Auto/Kanban.md")
JOBS_DIR_DEFAULT = Path("/vault/06-Career/Jobs")

# Columns in order
COLUMNS = [
    ("🔍 Scored", "scored"),
    ("📝 Applying", "applying"),
    ("✉️ Applied", "applied"),
    ("📞 Interview", "interview"),
    ("✅ Offer", "offer"),
    ("❌ Rejected", "rejected"),
]

# Status → column mapping (case-insensitive)
STATUS_MAP = {
    "scored": "scored",
    "new": "scored",
    "not started": "scored",
    "applying": "applying",
    "applied": "applied",
    "phone screen": "interview",
    "technical interview": "interview",
    "on-site interview": "interview",
    "interview": "interview",
    "offer": "offer",
    "rejected": "rejected",
    "withdrawn": "rejected",
}


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    fm = {}
    for line in parts[1].strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def scan_jobs(jobs_dir: Path) -> list[dict]:
    """Scan job.md files in the vault and return structured data."""
    jobs = []
    if not jobs_dir.exists():
        return jobs

    # Scan subdirectories: Company/Role/job.md
    for job_file in jobs_dir.rglob("job.md"):
        content = job_file.read_text(errors="replace")
        fm = parse_frontmatter(content)
        if not fm or fm.get("type") != "job":
            continue

        company = fm.get("company", "Unknown")
        role = fm.get("role", "Unknown")
        status = fm.get("status", "Scored").lower()
        score = fm.get("score", "?")
        location = fm.get("location", "")
        column = STATUS_MAP.get(status, "scored")

        # Build wikilink to the job file
        rel = job_file.relative_to(jobs_dir)
        link = f"[[06-Career/Jobs/{str(rel)}|{company}]]"

        jobs.append({
            "company": company,
            "role": role,
            "status": status,
            "score": score,
            "location": location,
            "column": column,
            "link": link,
            "display": f"- [ ] **{role}** — {link} ({score}/10, {location})",
        })

    # Also scan flat files (legacy)
    for job_file in jobs_dir.glob("*.md"):
        if job_file.name.startswith("README"):
            continue
        content = job_file.read_text(errors="replace")
        fm = parse_frontmatter(content)
        if not fm or fm.get("type") != "job":
            continue

        company = fm.get("company", job_file.stem)
        role = fm.get("role", job_file.stem)
        status = fm.get("status", "Scored").lower()
        score = fm.get("score", "?")
        location = fm.get("location", "")
        column = STATUS_MAP.get(status, "scored")

        link = f"[[06-Career/Jobs/{job_file.name}|{company}]]"
        jobs.append({
            "company": company,
            "role": role,
            "status": status,
            "score": score,
            "location": location,
            "column": column,
            "link": link,
            "display": f"- [ ] **{role}** — {link} ({score}/10, {location})",
        })

    return jobs


def build_kanban(jobs: list[dict]) -> str:
    """Build the kanban board content."""
    lines = ["---", "kanban-plugin: board", "---", ""]

    # Sort by score descending within each column
    by_column = {}
    for job in jobs:
        by_column.setdefault(job["column"], []).append(job)

    for col_title, col_key in COLUMNS:
        lines.append(f"## {col_title}")
        col_jobs = sorted(
            by_column.get(col_key, []),
            key=lambda j: float(j["score"]) if str(j["score"]).replace(".", "").isdigit() else 0,
            reverse=True,
        )
        if col_jobs:
            for job in col_jobs:
                lines.append(job["display"])
        else:
            lines.append("")
        lines.append("")

    # Kanban plugin settings
    lines.append("%% kanban:settings")
    lines.append("```")
    lines.append('{"kanban-plugin":"board"}')
    lines.append("```")
    lines.append("%%")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Rebuild Kanban from vault jobs")
    parser.add_argument("--kanban", type=Path, default=KANBAN_DEFAULT)
    parser.add_argument("--jobs-dir", type=Path, default=JOBS_DIR_DEFAULT)
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing")
    args = parser.parse_args()

    jobs = scan_jobs(args.jobs_dir)
    content = build_kanban(jobs)

    if args.dry_run:
        print(content)
    else:
        args.kanban.parent.mkdir(parents=True, exist_ok=True)
        args.kanban.write_text(content)
        print(f"Kanban updated: {len(jobs)} jobs across {len(set(j['column'] for j in jobs))} columns")

    return len(jobs)


if __name__ == "__main__":
    main()
