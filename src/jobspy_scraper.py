"""Job discovery using JobSpy library."""
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from jobspy import scrape_jobs
from .config import Config


class JobScraper:
    """Scrape jobs from multiple boards using JobSpy."""
    
    def __init__(self, config: Config):
        self.config = config
        self.searches = config.searches.get("searches", [])
    
    def discover_jobs(self, hours_old: int = 24) -> pd.DataFrame:
        """Run all configured searches and return combined results."""
        all_jobs = []
        
        for search in self.searches:
            try:
                df = self._run_search(search, hours_old)
                if not df.empty:
                    all_jobs.append(df)
            except Exception as e:
                print(f"Search failed for '{search.get('query')}': {e}")
                continue
        
        if not all_jobs:
            return pd.DataFrame()
        
        combined = pd.concat(all_jobs, ignore_index=True)
        combined = combined.drop_duplicates(subset=["title", "company"], keep="first")
        return combined
    
    def _run_search(self, search: dict, hours_old: int) -> pd.DataFrame:
        """Execute a single job search."""
        job_boards = search.get("job_boards", ["linkedin", "indeed"])
        site_names = []
        
        board_map = {
            "linkedin": "linkedin",
            "indeed": "indeed", 
            "glassdoor": "glassdoor",
            "google": "google",
        }
        for board in job_boards:
            if board in board_map:
                site_names.append(board_map[board])
        
        if not site_names:
            site_names = ["linkedin"]
        
        kwargs = {
            "site_name": site_names,
            "search_term": search["query"],
            "location": search.get("location", "Vancouver, BC"),
            "results_wanted": 50,
            "hours_old": hours_old,
            "country_indeed": "Canada",
        }
        
        if search.get("distance"):
            kwargs["distance"] = search["distance"]
        
        if search.get("remote_only"):
            kwargs["is_remote"] = True
        
        df = scrape_jobs(**kwargs)
        return df
