"""AI-powered job scoring using Z.ai GLM-4.7."""
from datetime import datetime
import json
import os
import httpx
from openai import OpenAI
from ..config import Config


class ScoringEngine:
    """Score jobs using GLM-4.7 based on location, experience, and skills."""
    
    def __init__(self, config: Config):
        self.config = config
        self.rules = config.scoring_rules
        self.profile = config.profile
        self.resume_facts = config.resume_facts
        
        # Explicit httpx timeout: 10s connect, 45s read, 45s total
        timeout_config = httpx.Timeout(45.0, connect=10.0)
        
        self.client = OpenAI(
            api_key=config.ai.get("api_key", ""),
            base_url=config.ai.get("base_url", "https://open.bigmodel.cn/api/coding/paas/v4"),
            timeout=timeout_config,
        )
        self.model = config.ai.get("model", "glm-4.7")
    
    def score_job(self, job: dict) -> dict:
        """Score a single job. Returns {score, breakdown, reasoning}."""
        weights = self.rules.get("weights", {})
        threshold = self.rules.get("threshold", 6.0)

        # Summarize skills instead of dumping raw JSON (saves ~3KB per call, faster API response)
        skills = self.resume_facts.get("skills", {})
        skills_flat = []
        for category, items in skills.items():
            if isinstance(items, list):
                skills_flat.extend(items[:5])  # Top 5 per category
            elif isinstance(items, str):
                skills_flat.append(items)
        skills_summary = ", ".join(skills_flat[:20])  # Cap at 20 skills

        # Summarize experience (titles + companies only, not full bullets)
        experience = self.resume_facts.get("experience", [])
        exp_summary = "; ".join([
            f"{e.get('title', '?')} at {e.get('company', '?')} ({e.get('dates', '?')})"
            for e in experience[:3]
        ])

        prompt = f"""Score this job for the candidate. Reply ONLY with JSON.

Candidate: {self.profile.get('personal', {}).get('location', 'Vancouver, BC')}, roles: {', '.join(self.profile.get('target_roles', [])[:4])}.
Skills: {skills_summary}.
Experience: {exp_summary}.

Job: {job.get('title', 'N/A')} at {job.get('company', 'N/A')}, {job.get('location', 'N/A')}.
Desc: {str(job.get('description', 'N/A'))[:1000]}

Weights: location {weights.get('location', 0.4)*100:.0f}%, exp {weights.get('experience', 0.3)*100:.0f}%, skills {weights.get('skills', 0.3)*100:.0f}%.
Threshold: {threshold}/10.

JSON only: {{"location_score": 1-10, "experience_score": 1-10, "skills_score": 1-10, "reasoning": "brief"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.config.ai.get("temperature", 0.3),
                max_tokens=300,  # JSON response only needs ~200 chars
            )
            text = response.choices[0].message.content.strip()
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(text)
            
            # Verify weighted calculation
            w = weights
            calculated = (
                result["location_score"] * w.get("location", 0.4) +
                result["experience_score"] * w.get("experience", 0.3) +
                result["skills_score"] * w.get("skills", 0.3)
            )
            result["weighted_total"] = round(calculated, 2)
            result["passes_threshold"] = calculated >= self.rules.get("threshold", 6.0)
            
            return result
            
        except Exception as e:
            return {
                "location_score": 0,
                "experience_score": 0,
                "skills_score": 0,
                "weighted_total": 0,
                "reasoning": f"Scoring error: {str(e)}",
                "passes_threshold": False,
            }
    
    def score_jobs(self, jobs: list[dict]) -> list[dict]:
        """Score multiple jobs and attach scores."""
        scored = []
        total = len(jobs)
        for idx, job in enumerate(jobs):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scoring job {idx+1}/{total}: {job.get('title', 'N/A')}")
            score_result = self.score_job(job)
            job["score"] = score_result
            scored.append(job)
        
        # Sort by score descending
        scored.sort(key=lambda x: x.get("score", {}).get("weighted_total", 0), reverse=True)
        return scored
