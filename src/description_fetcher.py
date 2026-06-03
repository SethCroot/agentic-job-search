#!/usr/bin/env python3
"""Fetch job descriptions for scored jobs that have no description.

LinkedIn via JobSpy returns None for descriptions. This module fetches them
by scraping the LinkedIn job page (no auth needed for public job listings).

Usage:
    python3 -m src.description_fetcher [--jobs-dir PATH] [--limit N]

Strategy:
- Scan scored jobs in vault with empty/None descriptions
- Fetch description from LinkedIn public job page via httpx
- Parse the description from HTML (no browser needed for public listings)
- Update the job.md file with the fetched description
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import Config


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    return parts[1], parts[2]


def has_description(body: str) -> bool:
    """Check if the body has a real description (not None/empty)."""
    desc_match = re.search(r"## Description\n(.+?)(?:\n##|\Z)", body, re.DOTALL)
    if not desc_match:
        return False
    desc = desc_match.group(1).strip()
    return desc and desc.lower() != "none" and len(desc) > 50


def fetch_linkedin_description(url: str, client: httpx.Client) -> str | None:
    """Fetch job description from a LinkedIn job page URL."""
    if not url or "linkedin.com" not in url:
        return None

    try:
        # LinkedIn public job pages work without auth
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = client.get(url, headers=headers, follow_redirects=True, timeout=15)

        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try multiple selectors for the description
        selectors = [
            ".show-more-less-html__markup",
            ".description__text",
            ".jobs-description__content",
            "#job-details",
            ".jobs-box__html-content",
        ]

        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 100:
                    return text

        # Fallback: look for any large text block that looks like a job description
        for tag in soup.find_all("div"):
            text = tag.get_text(strip=True)
            if len(text) > 500 and any(
                kw in text.lower() for kw in ["the role", "responsibilities", "qualifications", "requirements", "you will"]
            ):
                return text

        return None

    except Exception as e:
        print(f"    Fetch error: {e}")
        return None


def update_job_description(job_path: Path, description: str) -> None:
    """Update the job.md file with the fetched description."""
    content = job_path.read_text()

    # Replace the description section
    new_desc = f"## Description\n{description}\n"
    content = re.sub(
        r"## Description\n.*?(?=\n##|\Z)",
        new_desc,
        content,
        flags=re.DOTALL,
    )

    job_path.write_text(content)


def fetch_descriptions(jobs_dir: Path, limit: int = 0) -> dict:
    """Fetch descriptions for all scored jobs missing them."""
    stats = {"scanned": 0, "missing": 0, "fetched": 0, "failed": 0, "skipped_no_url": 0}

    client = httpx.Client()

    try:
        for job_file in sorted(jobs_dir.rglob("job.md")):
            stats["scanned"] += 1
            content = job_file.read_text()
            fm_text, body = parse_frontmatter(content)

            if has_description(body):
                continue

            # Parse URL from frontmatter
            url = None
            for line in fm_text.split("\n"):
                if line.startswith("url:"):
                    url = line.split(":", 1)[1].strip()
                    break

            if not url or "http" not in url:
                stats["skipped_no_url"] += 1
                continue

            stats["missing"] += 1
            if limit and stats["missing"] > limit:
                break

            # Get company/role for logging
            company = "Unknown"
            role = "Unknown"
            for line in fm_text.split("\n"):
                if line.startswith("company:"):
                    company = line.split(":", 1)[1].strip()
                elif line.startswith("role:"):
                    role = line.split(":", 1)[1].strip()

            print(f"  [{stats['missing']}] {company} — {role}")
            print(f"      URL: {url}")

            # Rate limit: be polite to LinkedIn
            time.sleep(1.5)

            desc = fetch_linkedin_description(url, client)
            if desc:
                update_job_description(job_file, desc)
                stats["fetched"] += 1
                print(f"      ✓ Fetched {len(desc)} chars")
            else:
                stats["failed"] += 1
                print(f"      ✗ Could not fetch description")

    finally:
        client.close()

    return stats


def main():
    parser = argparse.ArgumentParser(description="Fetch descriptions for scored jobs")
    parser.add_argument("--jobs-dir", default="/vault/06-Career/Jobs", help="Jobs directory")
    parser.add_argument("--limit", type=int, default=0, help="Max jobs to fetch (0 = all)")
    args = parser.parse_args()

    jobs_dir = Path(args.jobs_dir)
    if not jobs_dir.exists():
        print(f"Jobs directory not found: {jobs_dir}")
        sys.exit(1)

    print(f"Scanning {jobs_dir} for jobs missing descriptions...")
    stats = fetch_descriptions(jobs_dir, limit=args.limit)

    print(f"\n{'='*50}")
    print(f"Description Fetcher Results")
    print(f"{'='*50}")
    print(f"Scanned:    {stats['scanned']}")
    print(f"Missing:    {stats['missing']}")
    print(f"Fetched:    {stats['fetched']}")
    print(f"Failed:     {stats['failed']}")
    print(f"No URL:     {stats['skipped_no_url']}")


if __name__ == "__main__":
    main()
