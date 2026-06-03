"""Pre-filtering and deduplication before LLM scoring.

Saves tokens by removing jobs that don't need AI evaluation.
Dedup uses a persistent seen_jobs.csv so jobs are never re-scored
even if deleted from Obsidian.
"""
import csv
import re
from datetime import datetime
from pathlib import Path
from .config import Config


# Titles matching these regex patterns (case-insensitive) are auto-rejected.
# Using word boundaries (\b) to avoid false positives like "internal" matching "intern".
REJECT_TITLE_PATTERNS = [
    r"\bcashier\b", r"\bstock associate\b", r"\bshelf stocker\b", r"\bloader\b",
    r"\bdriver\b", r"\bcook\b", r"\bdishwasher\b", r"\bjanitor\b", r"\bcleaner\b",
    r"\bsecurity guard\b", r"\bbartender\b", r"\bbarista\b", r"\bserver\b",
    r"\bwaiter\b", r"\bwaitress\b", r"\bhost\b", r"\bretail associate\b",
    r"\bsales associate\b", r"\bfloor associate\b", r"\bwarehouse worker\b",
    r"\bforklift\b", r"\bdelivery driver\b", r"\bcourier\b",
    r"\bbabysitter\b", r"\bnanny\b", r"\bdog walker\b", r"\bpet sitter\b",
    r"\bintern(?:ship)?\b", r"\bapprentice\b", r"\bvolunteer\b", r"\bunpaid\b",
    r"\bbeauty advisor\b", r"\bmakeup artist\b", r"\bstylist\b",
    r"\bfront desk\b", r"\breceptionist\b", r"\bcash office\b",
]

# Pre-compile patterns for performance
_REJECT_COMPILED = [re.compile(p, re.IGNORECASE) for p in REJECT_TITLE_PATTERNS]

# If location contains none of these, it's likely outside target area.
# "Remote" is included since Seth accepts remote roles.
LOCATION_WHITELIST = [
    "vancouver", "bc", "british columbia", "remote", "hybrid",
    "burnaby", "richmond", "surrey", "north vancouver",
]

# CSV columns
SEEN_FIELDS = ["company", "title", "first_seen", "last_seen"]


class JobPreFilter:
    """Filter and deduplicate jobs before scoring."""

    def __init__(self, config: Config):
        self.config = config
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.seen_file = self.data_dir / "seen_jobs.csv"
        self._seen_keys: set[str] | None = None

    @property
    def seen_keys(self) -> set[str]:
        """Lazily load set of seen job keys from CSV."""
        if self._seen_keys is None:
            self._seen_keys = self._load_seen()
        return self._seen_keys

    def _load_seen(self) -> set[str]:
        """Load seen job keys from seen_jobs.csv."""
        keys = set()
        if not self.seen_file.exists():
            return keys

        with open(self.seen_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['company'].strip()}|{row['title'].strip()}"
                keys.add(key.lower())

        return keys

    def _job_key(self, job: dict) -> str:
        """Generate a dedup key for a job (company|title)."""
        company = str(job.get("company", "")).lower().strip()
        title = str(job.get("title", "")).lower().strip()
        return f"{company}|{title}"

    def _mark_seen(self, jobs: list[dict]) -> None:
        """Append newly processed jobs to seen_jobs.csv."""
        today = datetime.now().strftime("%Y-%m-%d")
        file_exists = self.seen_file.exists()

        with open(self.seen_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SEEN_FIELDS)
            if not file_exists:
                writer.writeheader()

            for job in jobs:
                key = self._job_key(job)
                writer.writerow({
                    "company": str(job.get("company", "")).strip(),
                    "title": str(job.get("title", "")).strip(),
                    "first_seen": today,
                    "last_seen": today,
                })
                self._seen_keys.add(key)

    def deduplicate(self, jobs: list[dict]) -> tuple[list[dict], int]:
        """Remove jobs already seen (in seen_jobs.csv).

        Returns (new_jobs, skipped_count).
        """
        new = []
        for job in jobs:
            key = self._job_key(job)
            if key not in self.seen_keys:
                new.append(job)

        skipped = len(jobs) - len(new)
        return new, skipped

    def mark_all_seen(self, jobs: list[dict]) -> None:
        """Mark jobs as seen after they've been scored.

        Call this AFTER scoring to ensure even low-scoring jobs
        are tracked and never re-scored.
        """
        self._mark_seen(jobs)

    def prefilter(self, jobs: list[dict]) -> tuple[list[dict], dict]:
        """Remove obviously irrelevant jobs without LLM.

        Returns (filtered_jobs, stats_dict).
        """
        stats = {"rejected_title": 0, "rejected_location": 0, "kept": 0}
        filtered = []

        for job in jobs:
            title = str(job.get("title", "")).lower()
            location = str(job.get("location", "")).lower()

            # Check title against reject patterns (word-boundary safe)
            rejected = False
            for pattern in _REJECT_COMPILED:
                if pattern.search(title):
                    stats["rejected_title"] += 1
                    rejected = True
                    break

            if rejected:
                continue

            # Check location — must contain at least one whitelisted term
            if location:
                location_ok = any(term in location for term in LOCATION_WHITELIST)
                if not location_ok:
                    stats["rejected_location"] += 1
                    continue

            filtered.append(job)
            stats["kept"] += 1

        return filtered, stats
