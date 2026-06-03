"""Main pipeline engine for Seth JobSearch Auto."""
from datetime import datetime
from .config import Config
from .jobspy_scraper import JobScraper
from .scoring import ScoringEngine
from .tailoring import TailoringEngine
from .cover_letter import CoverLetterGenerator
from .vault import VaultWriter
from .prefilter import JobPreFilter


class PipelineEngine:
    """Orchestrate the full job search pipeline."""
    
    def __init__(self, config: Config = None, dry_run: bool = False):
        self.config = config or Config()
        self.dry_run = dry_run
        self.scraper = JobScraper(self.config)
        self.scorer = ScoringEngine(self.config)
        self.tailor = TailoringEngine(self.config)
        self.cover_gen = CoverLetterGenerator(self.config)
        self.vault = VaultWriter(self.config)
        self.prefilter = JobPreFilter(self.config)
    
    def run(self, discover_only: bool = False, score_only: bool = False, limit: int = None) -> dict:
        """Execute the full pipeline."""
        results = {
            "discovered": 0,
            "scored": 0,
            "passed": 0,
            "cover_letters": 0,
            "top_jobs": [],
            "errors": [],
            "deduped": 0,
            "filtered_title": 0,
            "filtered_location": 0,
        }
        
        # Phase 1: Discover jobs
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [1/5] Discovering jobs...")
        num_searches = len(self.config.searches.get('searches', []))
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Running {num_searches} searches across LinkedIn + Indeed...")
        try:
            df = self.scraper.discover_jobs(hours_old=24)
            results["discovered"] = len(df)
            jobs = df.to_dict("records") if not df.empty else []
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Discovery complete: {results['discovered']} jobs found")
        except Exception as e:
            results["errors"].append(f"Discovery failed: {e}")
            return results
        
        if not jobs:
            print("No jobs found.")
            return results
        
        print(f"  Found {len(jobs)} jobs")
        
        if limit and len(jobs) > limit:
            print(f"  Limiting to {limit} jobs for this run")
            jobs = jobs[:limit]
        
        if discover_only:
            print("  [discover-only mode] Skipping filtering, scoring and tailoring.")
            results["top_jobs"] = jobs[:10]
            return results
        
        # Phase 2: Deduplicate against vault
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [2/5] Deduplicating against vault...")
        jobs, deduped = self.prefilter.deduplicate(jobs)
        results["deduped"] = deduped
        print(f"  {deduped} jobs already in vault, {len(jobs)} new jobs to evaluate")
        
        if not jobs:
            print("  All jobs already processed. Nothing new to score.")
            self.vault.write_daily_digest(results)
            return results
        
        # Phase 3: Pre-filter obviously irrelevant jobs
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [3/5] Pre-filtering {len(jobs)} new jobs...")
        jobs, filter_stats = self.prefilter.prefilter(jobs)
        results["filtered_title"] = filter_stats["rejected_title"]
        results["filtered_location"] = filter_stats["rejected_location"]
        print(f"  Rejected: {filter_stats['rejected_title']} by title, {filter_stats['rejected_location']} by location")
        print(f"  {len(jobs)} jobs survive pre-filter → sending to LLM")
        
        if not jobs:
            print("  No jobs survived pre-filter.")
            self.vault.write_daily_digest(results)
            return results
        
        # Phase 4: Score jobs
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [4/5] Scoring {len(jobs)} jobs with GLM-4.7...")
        estimated_min = len(jobs) * 10 / 60
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Estimated: ~{estimated_min:.0f} minutes ({len(jobs)} jobs × ~10s each)")
        scored_jobs = self.scorer.score_jobs(jobs)
        passing = [j for j in scored_jobs if j.get("score", {}).get("passes_threshold", False)]
        results["scored"] = len(scored_jobs)
        results["passed"] = len(passing)
        results["top_jobs"] = passing[:10]

        # Mark ALL scored jobs as seen (even failures) so they're never re-scored
        self.prefilter.mark_all_seen(scored_jobs)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scoring complete: {len(passing)} jobs passed threshold (≥{self.config.scoring_rules.get('threshold', 7.5)})")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(scored_jobs)} jobs marked as seen in dedup database")
        
        if score_only:
            print("  [score-only mode] Skipping tailoring and cover letters.")
            self.vault.write_daily_digest(results)
            return results
        
        if not passing:
            print("No jobs passed threshold.")
            self.vault.write_daily_digest(results)
            return results
        
        # Phase 5: Tailor + Cover Letters for top matches
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [5/5] Tailoring resumes and generating cover letters for top {min(len(passing), 10)} jobs...")
        for idx, job in enumerate(passing[:10], 1):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processing job {idx}/{min(len(passing), 10)}: {job.get('title')} at {job.get('company')}")
            if self.dry_run:
                job["tailoring"] = {"summary": "[DRY RUN - no tailoring]", "highlighted_experience": [], "highlighted_skills": []}
                job["cover_letter"] = "[DRY RUN - no cover letter]"
                continue

            try:
                tailoring = self.tailor.tailor_for_job(job)
                job["tailoring"] = tailoring

                cover = self.cover_gen.generate(job, tailoring)
                job["cover_letter"] = cover
                results["cover_letters"] += 1
            except Exception as e:
                results["errors"].append(f"Tailoring failed for {job.get('title')}: {e}")
                job["tailoring"] = {"error": str(e)}
                job["cover_letter"] = ""

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Tailoring complete: {results['cover_letters']} cover letters generated")
        
        # Write to vault
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Writing {len(passing)} jobs to Obsidian vault...")
        for job in passing:
            if not self.dry_run:
                try:
                    self.vault.write_job(job)
                except Exception as e:
                    results["errors"].append(f"Vault write failed for {job.get('title')}: {e}")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Vault writes complete")

        # Daily digest
        self.vault.write_daily_digest(results)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Daily digest written to {self.config.daily_dir / datetime.now().strftime('%Y-%m-%d.md')}")
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Pipeline complete. {results['passed']} jobs ready for review.")
        return results
